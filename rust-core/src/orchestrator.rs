/*!
 * KYC Orchestrator
 * Coordinates the workflow between all AI agents
 */

use anyhow::{Result, Context};
use serde::{Deserialize, Serialize};
use std::sync::Arc;
use std::collections::HashMap;
use tracing::{info, error, debug, warn};
use chrono::{DateTime, Utc};

use crate::{
    config::AppConfig,
    messaging::MessageBus,
    database::DatabaseManager,
    monitoring::MetricsCollector,
    agents::AgentClient,
    KYCDecision, ProcessingStage,
};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct KYCResult {
    pub session_id: String,
    pub customer_id: String,
    pub decision: KYCDecision,
    pub confidence_score: f64,
    pub processing_time: f64,
    pub agent_results: HashMap<String, serde_json::Value>,
    pub compliance_status: String,
    pub risk_score: f64,
    pub recommendations: Vec<String>,
    pub completed_at: DateTime<Utc>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AgentResult {
    pub agent_name: String,
    pub status: String,
    pub result: serde_json::Value,
    pub processing_time: f64,
    pub error: Option<String>,
}

pub struct KYCOrchestrator {
    config: Arc<AppConfig>,
    message_bus: Arc<MessageBus>,
    database: Arc<DatabaseManager>,
    metrics: Arc<MetricsCollector>,
    agent_clients: HashMap<String, AgentClient>,
}

impl KYCOrchestrator {
    pub async fn new(
        config: Arc<AppConfig>,
        message_bus: Arc<MessageBus>,
        database: Arc<DatabaseManager>,
        metrics: Arc<MetricsCollector>,
    ) -> Result<Self> {
        info!("Initializing KYC orchestrator...");
        
        // Initialize agent clients
        let mut agent_clients = HashMap::new();
        
        agent_clients.insert(
            "data-ingestion".to_string(),
            AgentClient::new("data-ingestion", &config.agents.data_ingestion).await?,
        );
        
        agent_clients.insert(
            "kyc-analysis".to_string(),
            AgentClient::new("kyc-analysis", &config.agents.kyc_analysis).await?,
        );
        
        agent_clients.insert(
            "decision-making".to_string(),
            AgentClient::new("decision-making", &config.agents.decision_making).await?,
        );
        
        agent_clients.insert(
            "compliance-monitoring".to_string(),
            AgentClient::new("compliance-monitoring", &config.agents.compliance_monitoring).await?,
        );
        
        agent_clients.insert(
            "data-quality".to_string(),
            AgentClient::new("data-quality", &config.agents.data_quality).await?,
        );
        
        info!("KYC orchestrator initialized with {} agents", agent_clients.len());
        
        Ok(Self {
            config,
            message_bus,
            database,
            metrics,
            agent_clients,
        })
    }
    
    pub async fn process_kyc(
        &self,
        session_id: String,
        customer_id: String,
        customer_data: serde_json::Value,
        regulatory_requirements: Vec<String>,
    ) -> Result<KYCResult> {
        info!("Starting KYC processing for session: {}", session_id);
        let start_time = std::time::Instant::now();
        
        let mut agent_results = HashMap::new();
        
        // Stage 1: Data Quality Validation
        info!("Stage 1: Data Quality Validation");
        let quality_result = self.run_data_quality_check(&session_id, &customer_data).await?;
        agent_results.insert("data-quality".to_string(), quality_result.clone());
        
        // Check if data quality is acceptable
        let quality_score = quality_result.get("overall_score")
            .and_then(|v| v.as_f64())
            .unwrap_or(0.0);
        
        if quality_score < 0.6 {
            warn!("Data quality score too low: {}", quality_score);
            return Ok(KYCResult {
                session_id,
                customer_id,
                decision: KYCDecision::RequiresAdditionalInfo,
                confidence_score: quality_score,
                processing_time: start_time.elapsed().as_secs_f64(),
                agent_results,
                compliance_status: "data_quality_insufficient".to_string(),
                risk_score: 1.0,
                recommendations: vec!["Improve data quality before proceeding".to_string()],
                completed_at: Utc::now(),
            });
        }
        
        // Stage 2: Data Ingestion and Normalization
        info!("Stage 2: Data Ingestion and Normalization");
        let ingestion_result = self.run_data_ingestion(&session_id, &customer_data).await?;
        agent_results.insert("data-ingestion".to_string(), ingestion_result.clone());
        
        // Stage 3: KYC Analysis
        info!("Stage 3: KYC Analysis");
        let analysis_result = self.run_kyc_analysis(&session_id, &ingestion_result, &regulatory_requirements).await?;
        agent_results.insert("kyc-analysis".to_string(), analysis_result.clone());
        
        // Stage 4: Compliance Monitoring
        info!("Stage 4: Compliance Monitoring");
        let compliance_result = self.run_compliance_check(&session_id, &customer_data, &regulatory_requirements).await?;
        agent_results.insert("compliance-monitoring".to_string(), compliance_result.clone());
        
        // Stage 5: Decision Making
        info!("Stage 5: Decision Making");
        let decision_input = serde_json::json!({
            "customer_data": customer_data,
            "analysis_results": analysis_result,
            "compliance_results": compliance_result,
            "quality_results": quality_result
        });
        
        let decision_result = self.run_decision_making(&session_id, &decision_input).await?;
        agent_results.insert("decision-making".to_string(), decision_result.clone());
        
        // Extract final decision
        let final_decision = self.extract_final_decision(&decision_result)?;
        let confidence_score = decision_result.get("confidence_level")
            .and_then(|v| v.as_f64())
            .unwrap_or(0.5);
        
        let compliance_status = compliance_result.get("overall_status")
            .and_then(|v| v.as_str())
            .unwrap_or("unknown")
            .to_string();
        
        let risk_score = analysis_result.get("risk_assessment")
            .and_then(|v| v.get("risk_score"))
            .and_then(|v| v.as_f64())
            .unwrap_or(0.5);
        
        let recommendations = decision_result.get("recommendations")
            .and_then(|v| v.as_array())
            .map(|arr| arr.iter().filter_map(|v| v.as_str().map(|s| s.to_string())).collect())
            .unwrap_or_default();
        
        let processing_time = start_time.elapsed().as_secs_f64();
        
        // Update metrics
        self.metrics.record_kyc_processing(processing_time, &final_decision).await;
        
        let result = KYCResult {
            session_id: session_id.clone(),
            customer_id,
            decision: final_decision,
            confidence_score,
            processing_time,
            agent_results,
            compliance_status,
            risk_score,
            recommendations,
            completed_at: Utc::now(),
        };
        
        // Store result in database
        self.database.store_kyc_result(&result).await?;
        
        info!("KYC processing completed for session: {} in {:.2}s", session_id, processing_time);
        
        Ok(result)
    }
    
    async fn run_data_quality_check(&self, session_id: &str, customer_data: &serde_json::Value) -> Result<serde_json::Value> {
        debug!("Running data quality check for session: {}", session_id);
        
        let client = self.agent_clients.get("data-quality")
            .context("Data quality agent client not found")?;
        
        let request = serde_json::json!({
            "customer_id": session_id,
            "data_type": "personal_info",
            "data_payload": customer_data,
            "check_anomalies": true,
            "generate_profile": false
        });
        
        client.call_agent("/api/v1/quality/check", &request).await
    }
    
    async fn run_data_ingestion(&self, session_id: &str, customer_data: &serde_json::Value) -> Result<serde_json::Value> {
        debug!("Running data ingestion for session: {}", session_id);
        
        let client = self.agent_clients.get("data-ingestion")
            .context("Data ingestion agent client not found")?;
        
        let request = serde_json::json!({
            "customer_id": session_id,
            "data_sources": [customer_data],
            "processing_options": {
                "normalize_schema": true,
                "extract_entities": true,
                "validate_documents": true
            }
        });
        
        client.call_agent("/api/v1/data/ingest", &request).await
    }
    
    async fn run_kyc_analysis(&self, session_id: &str, ingested_data: &serde_json::Value, regulatory_requirements: &[String]) -> Result<serde_json::Value> {
        debug!("Running KYC analysis for session: {}", session_id);
        
        let client = self.agent_clients.get("kyc-analysis")
            .context("KYC analysis agent client not found")?;
        
        let request = serde_json::json!({
            "customer_id": session_id,
            "customer_data": ingested_data,
            "analysis_type": "full",
            "priority": "normal",
            "regulatory_requirements": regulatory_requirements
        });
        
        client.call_agent("/api/v1/kyc/analyze", &request).await
    }
    
    async fn run_compliance_check(&self, session_id: &str, customer_data: &serde_json::Value, regulatory_requirements: &[String]) -> Result<serde_json::Value> {
        debug!("Running compliance check for session: {}", session_id);
        
        let client = self.agent_clients.get("compliance-monitoring")
            .context("Compliance monitoring agent client not found")?;
        
        let regulation_types = if regulatory_requirements.is_empty() {
            vec!["aml".to_string(), "gdpr".to_string()]
        } else {
            regulatory_requirements.to_vec()
        };
        
        let request = serde_json::json!({
            "customer_id": session_id,
            "regulation_types": regulation_types,
            "customer_data": customer_data,
            "check_type": "full",
            "priority": "normal"
        });
        
        client.call_agent("/api/v1/compliance/check", &request).await
    }
    
    async fn run_decision_making(&self, session_id: &str, decision_input: &serde_json::Value) -> Result<serde_json::Value> {
        debug!("Running decision making for session: {}", session_id);
        
        let client = self.agent_clients.get("decision-making")
            .context("Decision making agent client not found")?;
        
        let request = serde_json::json!({
            "customer_id": session_id,
            "decision_type": "kyc_approval",
            "input_data": decision_input.get("customer_data").unwrap_or(&serde_json::Value::Null),
            "analysis_results": {
                "kyc_analysis": decision_input.get("analysis_results").unwrap_or(&serde_json::Value::Null),
                "compliance_results": decision_input.get("compliance_results").unwrap_or(&serde_json::Value::Null),
                "quality_results": decision_input.get("quality_results").unwrap_or(&serde_json::Value::Null)
            },
            "priority": "normal"
        });
        
        client.call_agent("/api/v1/decision/make", &request).await
    }
    
    fn extract_final_decision(&self, decision_result: &serde_json::Value) -> Result<KYCDecision> {
        let decision_str = decision_result.get("final_decision")
            .and_then(|v| v.as_str())
            .unwrap_or("requires_review");
        
        match decision_str.to_lowercase().as_str() {
            "approved" | "approve" => Ok(KYCDecision::Approved),
            "rejected" | "reject" => Ok(KYCDecision::Rejected),
            "requires_additional_info" => Ok(KYCDecision::RequiresAdditionalInfo),
            _ => Ok(KYCDecision::RequiresReview),
        }
    }
    
    pub async fn get_agents_status(&self) -> HashMap<String, crate::AgentStatus> {
        let mut status_map = HashMap::new();
        
        for (name, client) in &self.agent_clients {
            let status = match client.health_check().await {
                Ok(true) => crate::AgentStatus {
                    name: name.clone(),
                    status: "healthy".to_string(),
                    last_seen: Utc::now(),
                    health: true,
                    last_heartbeat: Utc::now(),
                    processed_requests: 0, // Would track in production
                    error_rate: 0.0,
                },
                Ok(false) | Err(_) => crate::AgentStatus {
                    name: name.clone(),
                    status: "unhealthy".to_string(),
                    last_seen: Utc::now(),
                    health: false,
                    last_heartbeat: Utc::now(),
                    processed_requests: 0,
                    error_rate: 1.0,
                },
            };
            
            status_map.insert(name.clone(), status);
        }
        
        status_map
    }
    
    pub async fn ingest_data(&self, data: serde_json::Value) -> Result<serde_json::Value> {
        let client = self.agent_clients.get("data-ingestion")
            .context("Data ingestion agent client not found")?;
        
        client.call_agent("/api/v1/data/ingest", &data).await
    }
    
    pub async fn check_compliance(&self, customer_id: &str) -> Result<serde_json::Value> {
        let client = self.agent_clients.get("compliance-monitoring")
            .context("Compliance monitoring agent client not found")?;
        
        let request = serde_json::json!({
            "customer_id": customer_id,
            "regulation_types": ["aml", "gdpr"],
            "customer_data": {},
            "check_type": "status_check"
        });
        
        client.call_agent("/api/v1/compliance/check", &request).await
    }
    
    pub async fn configure_industry(&self, config: serde_json::Value) -> Result<serde_json::Value> {
        // Industry configuration would update agent configurations
        // For now, return success
        Ok(serde_json::json!({
            "status": "success",
            "message": "Industry configuration updated",
            "config": config
        }))
    }
}
