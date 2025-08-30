use crate::config::Config;
use crate::messaging::{KafkaMessaging, KycRequest, KycResult, ProcessingStep};
use crate::storage::PineconeClient;
use anyhow::Result;
use chrono::{DateTime, Utc};
use rdkafka::consumer::StreamConsumer;
use rdkafka::Message;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::sync::Arc;
use tokio::time::{timeout, Duration};
use uuid::Uuid;

/// Main orchestrator for KYC workflow processing
/// Coordinates all agents according to the operational framework
pub struct KycOrchestrator {
    config: Arc<Config>,
    messaging: Arc<KafkaMessaging>,
    storage: Arc<PineconeClient>,
    http_client: reqwest::Client,
}

/// Agent response structure
/// Standardized response format from all processing agents
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AgentResponse {
    /// Agent name
    pub agent_name: String,
    /// Processing status
    pub status: AgentStatus,
    /// Response data
    pub data: serde_json::Value,
    /// Processing time in milliseconds
    pub processing_time: u64,
    /// Error message if any
    pub error: Option<String>,
    /// Agent version
    pub version: String,
}

/// Agent processing status
#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum AgentStatus {
    Success,
    Warning,
    Error,
    Timeout,
}

/// Workflow execution context
/// Tracks the state of KYC processing workflow
#[derive(Debug, Clone)]
pub struct WorkflowContext {
    /// Original request
    pub request: KycRequest,
    /// Agent responses
    pub agent_responses: HashMap<String, AgentResponse>,
    /// Processing start time
    pub start_time: DateTime<Utc>,
    /// Current processing step
    pub current_step: usize,
    /// Processing steps for audit trail
    pub processing_steps: Vec<ProcessingStep>,
}

impl KycOrchestrator {
    /// Create new KYC orchestrator instance
    /// Initializes all required components for workflow processing
    pub fn new(
        config: Arc<Config>,
        messaging: Arc<KafkaMessaging>,
        storage: Arc<PineconeClient>,
    ) -> Result<Self> {
        let http_client = reqwest::Client::builder()
            .timeout(Duration::from_secs(30))
            .build()
            .map_err(|e| anyhow::anyhow!("Failed to create HTTP client: {}", e))?;

        Ok(Self {
            config,
            messaging,
            storage,
            http_client,
        })
    }

    /// Start the orchestrator
    /// Begins consuming KYC requests and processing them through the workflow
    pub async fn start(&self) -> Result<()> {
        log::info!("Starting KYC orchestrator");
        
        // Subscribe to KYC request topic
        self.messaging.subscribe_to_requests()?;
        
        // Start processing loop
        loop {
            match self.process_next_request().await {
                Ok(_) => {},
                Err(e) => {
                    log::error!("Error processing request: {}", e);
                    // Continue processing other requests
                }
            }
        }
    }

    /// Process the next KYC request from Kafka
    /// Implements the complete operational framework workflow
    async fn process_next_request(&self) -> Result<()> {
        // Poll for messages with timeout
        use futures::StreamExt;
        let message = timeout(
            Duration::from_secs(1),
            self.messaging.request_consumer().recv()
        ).await;

        match message {
            Ok(Ok(msg)) => {
                if let Some(payload) = msg.payload() {
                    let request: KycRequest = serde_json::from_slice(payload)
                        .map_err(|e| anyhow::anyhow!("Failed to parse KYC request: {}", e))?;
                    
                    log::info!("Processing KYC request: {}", request.request_id);
                    
                    // Process the request through the workflow
                    let result = match self.execute_workflow(request.clone()).await {
                        Ok(result) => result,
                        Err(e) => {
                            log::error!("Workflow execution failed: {}", e);
                            // Create a fallback result with error information
                            self.create_error_result(request, e.to_string()).await
                        }
                    };
                    
                    // Try to store result in vector database (non-blocking)
                    match self.storage.store_kyc_result(&result).await {
                        Ok(_) => {
                            log::info!("Successfully stored KYC result in vector database: {}", result.request_id);
                        }
                        Err(e) => {
                            log::warn!("Failed to store KYC result in vector database (continuing anyway): {}", e);
                        }
                    }
                    
                    // Always publish result regardless of Pinecone status
                    self.messaging.produce_kyc_result(&result).await?;
                    
                    log::info!("Completed KYC request: {}", result.request_id);
                }
            }
            Ok(Err(e)) => {
                log::error!("Kafka consumer error: {}", e);
            }
            Err(_) => {
                // Timeout - continue polling
            }
        }

        Ok(())
    }

    /// Execute the complete KYC workflow
    /// Implements the 6-step operational framework
    async fn execute_workflow(&self, request: KycRequest) -> Result<KycResult> {
        let mut context = WorkflowContext {
            request: request.clone(),
            agent_responses: HashMap::new(),
            start_time: Utc::now(),
            current_step: 0,
            processing_steps: Vec::new(),
        };

        // Step 1: Document Verification Agent (OCR)
        if request.processing_config.enable_ocr {
            self.execute_step(&mut context, "ocr", &self.config.agents.ocr_agent).await?;
        }

        // Step 2: Identity Authentication Agent (Face Recognition)
        if request.processing_config.enable_face_recognition {
            self.execute_step(&mut context, "face", &self.config.agents.face_agent).await?;
        }

        // Step 3: Data Integration Agent
        if request.processing_config.enable_data_integration {
            self.execute_step(&mut context, "data_integration", &self.config.agents.data_integration_agent).await?;
        }

        // Step 4: Risk Assessment Agent (Watchlist)
        if request.processing_config.enable_watchlist_screening {
            self.execute_step(&mut context, "watchlist", &self.config.agents.watchlist_agent).await?;
        }

        // Step 5: Compliance Monitoring (integrated into other agents)
        // This is handled by each agent's compliance checks

        // Step 6: Quality Assurance Agent
        if request.processing_config.enable_qa {
            self.execute_step(&mut context, "qa", &self.config.agents.qa_agent).await?;
        }

        // Generate final result
        self.generate_final_result(context).await
    }

    /// Execute a single workflow step
    /// Calls the specified agent and records the response
    async fn execute_step(
        &self,
        context: &mut WorkflowContext,
        agent_name: &str,
        agent_endpoint: &str,
    ) -> Result<()> {
        let step_start = Utc::now();
        context.current_step += 1;

        log::info!("Executing step {}: {}", context.current_step, agent_name);

        // Prepare agent request
        let agent_request = self.prepare_agent_request(context, agent_name)?;

        // Call agent with timeout
        let response = match timeout(
            Duration::from_secs(30),
            self.call_agent(agent_endpoint, &agent_request)
        ).await {
            Ok(Ok(response)) => response,
            Ok(Err(e)) => {
                log::error!("Agent {} failed: {}", agent_name, e);
                AgentResponse {
                    agent_name: agent_name.to_string(),
                    status: AgentStatus::Error,
                    data: serde_json::json!({"error": e.to_string()}),
                    processing_time: (Utc::now() - step_start).num_milliseconds() as u64,
                    error: Some(e.to_string()),
                    version: "unknown".to_string(),
                }
            }
            Err(_) => {
                log::error!("Agent {} timed out", agent_name);
                AgentResponse {
                    agent_name: agent_name.to_string(),
                    status: AgentStatus::Timeout,
                    data: serde_json::json!({"error": "timeout"}),
                    processing_time: 30000,
                    error: Some("Agent timeout".to_string()),
                    version: "unknown".to_string(),
                }
            }
        };

        let step_end = Utc::now();

        // Record processing step for audit trail
        let processing_step = ProcessingStep {
            step_name: format!("Step {}: {}", context.current_step, agent_name),
            agent: agent_name.to_string(),
            start_time: step_start,
            end_time: step_end,
            status: format!("{:?}", response.status),
            details: response.data.clone(),
        };

        context.processing_steps.push(processing_step);
        context.agent_responses.insert(agent_name.to_string(), response);

        Ok(())
    }

    /// Prepare request data for agent
    /// Formats the request according to each agent's requirements
    fn prepare_agent_request(
        &self,
        context: &WorkflowContext,
        agent_name: &str,
    ) -> Result<serde_json::Value> {
        let base_request = serde_json::json!({
            "request_id": context.request.request_id,
            "timestamp": context.request.timestamp,
            "documents": context.request.documents,
            "customer_info": context.request.customer_info,
            "processing_config": context.request.processing_config,
            "previous_results": context.agent_responses
        });

        // Agent-specific request preparation
        let agent_request = match agent_name {
            "ocr" => {
                // OCR agent needs document files
                serde_json::json!({
                    "request_id": context.request.request_id,
                    "documents": context.request.documents.iter()
                        .filter(|d| d.document_type != "selfie")
                        .collect::<Vec<_>>()
                })
            }
            "face" => {
                // Face agent needs selfie and ID photo
                serde_json::json!({
                    "request_id": context.request.request_id,
                    "selfie": context.request.documents.iter()
                        .find(|d| d.document_type == "selfie"),
                    "id_photo": context.request.documents.iter()
                        .find(|d| d.document_type != "selfie"),
                    "ocr_results": context.agent_responses.get("ocr")
                })
            }
            "watchlist" => {
                // Watchlist agent needs extracted identity information
                serde_json::json!({
                    "request_id": context.request.request_id,
                    "identity_data": context.agent_responses.get("ocr"),
                    "customer_info": context.request.customer_info
                })
            }
            "data_integration" => {
                // Data integration agent needs all previous results
                base_request
            }
            "qa" => {
                // QA agent needs all results for validation
                serde_json::json!({
                    "request_id": context.request.request_id,
                    "all_results": context.agent_responses,
                    "processing_config": context.request.processing_config
                })
            }
            _ => base_request,
        };

        Ok(agent_request)
    }

    /// Call an agent endpoint
    /// Makes HTTP request to the specified agent service
    async fn call_agent(
        &self,
        endpoint: &str,
        request_data: &serde_json::Value,
    ) -> Result<AgentResponse> {
        let url = format!("{}/process", endpoint);
        
        let response = self.http_client
            .post(&url)
            .header("Content-Type", "application/json")
            .json(request_data)
            .send()
            .await
            .map_err(|e| anyhow::anyhow!("Failed to call agent: {}", e))?;

        if !response.status().is_success() {
            let error_text = response.text().await.unwrap_or_default();
            return Err(anyhow::anyhow!("Agent returned error: {}", error_text));
        }

        let agent_response: AgentResponse = response
            .json()
            .await
            .map_err(|e| anyhow::anyhow!("Failed to parse agent response: {}", e))?;

        Ok(agent_response)
    }

    /// Generate final KYC result
    /// Aggregates all agent responses into comprehensive result
    async fn generate_final_result(&self, context: WorkflowContext) -> Result<KycResult> {
        let processing_time = (Utc::now() - context.start_time).num_milliseconds() as u64;
        
        // Calculate overall risk score
        let risk_score = self.calculate_risk_score(&context.agent_responses);
        
        // Calculate confidence score
        let confidence = self.calculate_confidence(&context.agent_responses);
        
        // Determine recommendation
        let recommendation = self.determine_recommendation(risk_score, confidence, &context.agent_responses);
        
        // Extract QA verdict
        let qa_verdict = self.extract_qa_verdict(&context.agent_responses);
        
        // Generate executive summary
        let executive_summary = crate::messaging::ExecutiveSummary {
            recommendation,
            risk_score,
            confidence,
            processing_time,
            cost_savings: self.calculate_cost_savings(processing_time),
        };

        // Generate detailed analysis
        let detailed_analysis = crate::messaging::DetailedAnalysis {
            ocr_results: context.agent_responses.get("ocr").map(|r| r.data.clone()),
            biometric_results: context.agent_responses.get("face").map(|r| r.data.clone()),
            watchlist_results: context.agent_responses.get("watchlist").map(|r| r.data.clone()),
            data_integration_results: context.agent_responses.get("data_integration").map(|r| r.data.clone()),
            risk_assessment: Some(serde_json::json!({
                "risk_score": risk_score,
                "risk_factors": self.identify_risk_factors(&context.agent_responses)
            })),
        };

        // Generate audit trail
        let audit_trail = crate::messaging::AuditTrail {
            processing_steps: context.processing_steps,
            data_sources: self.extract_data_sources(&context.agent_responses),
            rules_applied: self.extract_rules_applied(&context.agent_responses),
            agent_versions: context.agent_responses.iter()
                .map(|(name, response)| (name.clone(), response.version.clone()))
                .collect(),
        };

        // Generate actionable insights
        let actionable_insights = self.generate_actionable_insights(&context.agent_responses, risk_score);

        Ok(KycResult {
            request_id: context.request.request_id,
            timestamp: Utc::now(),
            executive_summary,
            detailed_analysis,
            audit_trail,
            actionable_insights,
            qa_verdict,
        })
    }

    /// Calculate overall risk score from agent responses
    /// Combines risk indicators from all agents
    fn calculate_risk_score(&self, responses: &HashMap<String, AgentResponse>) -> f64 {
        let mut total_score = 0.0;
        let mut weight_sum = 0.0;

        // OCR risk factors (weight: 0.2)
        if let Some(ocr_response) = responses.get("ocr") {
            let score = ocr_response.data.get("risk_score").unwrap_or(&serde_json::json!(0.0)).as_f64().unwrap_or(0.0);
            total_score += score * 0.2;
            weight_sum += 0.2;
        }

        // Face recognition risk factors (weight: 0.3)
        if let Some(face_response) = responses.get("face") {
            let match_score = face_response.data.get("match_score").unwrap_or(&serde_json::json!(100.0)).as_f64().unwrap_or(100.0);
            let face_risk = (100.0 - match_score).max(0.0);
            total_score += face_risk * 0.3;
            weight_sum += 0.3;
        }

        // Watchlist risk factors (weight: 0.4)
        if let Some(watchlist_response) = responses.get("watchlist") {
            let is_flagged = watchlist_response.data.get("flagged").unwrap_or(&serde_json::json!(false)).as_bool().unwrap_or(false);
            let watchlist_risk = if is_flagged { 90.0 } else { 10.0 };
            total_score += watchlist_risk * 0.4;
            weight_sum += 0.4;
        }

        // Data integration risk factors (weight: 0.1)
        if let Some(data_response) = responses.get("data_integration") {
            let score = data_response.data.get("risk_score").unwrap_or(&serde_json::json!(0.0)).as_f64().unwrap_or(0.0);
            total_score += score * 0.1;
            weight_sum += 0.1;
        }

        if weight_sum > 0.0 {
            total_score / weight_sum
        } else {
            50.0 // Default medium risk if no data available
        }
    }

    /// Calculate confidence score from agent responses
    /// Measures the reliability of the overall assessment
    fn calculate_confidence(&self, responses: &HashMap<String, AgentResponse>) -> f64 {
        let mut confidence_sum = 0.0;
        let mut count = 0;

        for response in responses.values() {
            match response.status {
                AgentStatus::Success => {
                    confidence_sum += 95.0;
                    count += 1;
                }
                AgentStatus::Warning => {
                    confidence_sum += 70.0;
                    count += 1;
                }
                AgentStatus::Error | AgentStatus::Timeout => {
                    confidence_sum += 30.0;
                    count += 1;
                }
            }
        }

        if count > 0 {
            confidence_sum / count as f64
        } else {
            50.0
        }
    }

    /// Determine final recommendation based on risk and confidence
    /// Implements business logic for KYC decision making
    fn determine_recommendation(
        &self,
        risk_score: f64,
        confidence: f64,
        responses: &HashMap<String, AgentResponse>,
    ) -> crate::messaging::Recommendation {
        // Check for immediate rejection criteria
        if let Some(watchlist_response) = responses.get("watchlist") {
            if watchlist_response.data.get("flagged").unwrap_or(&serde_json::json!(false)).as_bool().unwrap_or(false) {
                return crate::messaging::Recommendation::Reject;
            }
        }

        // Check QA failures
        if let Some(qa_response) = responses.get("qa") {
            if qa_response.data.get("status").unwrap_or(&serde_json::json!("passed")).as_str().unwrap_or("passed") == "failed" {
                return crate::messaging::Recommendation::Reject;
            }
        }

        // Risk-based decision making
        match (risk_score, confidence) {
            (r, c) if r <= 20.0 && c >= 90.0 => crate::messaging::Recommendation::Approve,
            (r, c) if r <= 40.0 && c >= 80.0 => crate::messaging::Recommendation::Conditional,
            (r, c) if r <= 60.0 && c >= 70.0 => crate::messaging::Recommendation::Escalate,
            (r, _) if r > 60.0 => crate::messaging::Recommendation::Reject,
            (_, c) if c < 70.0 => crate::messaging::Recommendation::Escalate,
            _ => crate::messaging::Recommendation::Escalate,
        }
    }

    /// Extract QA verdict from responses
    /// Processes quality assurance agent results
    fn extract_qa_verdict(&self, responses: &HashMap<String, AgentResponse>) -> crate::messaging::QaVerdict {
        if let Some(qa_response) = responses.get("qa") {
            let default_status = serde_json::json!("passed");
            let status_str = qa_response.data.get("status").unwrap_or(&default_status).as_str().unwrap_or("passed");
            let status = match status_str {
                "passed" => crate::messaging::QaStatus::Passed,
                "failed" => crate::messaging::QaStatus::Failed,
                "warning" => crate::messaging::QaStatus::Warning,
                "manual_review" => crate::messaging::QaStatus::ManualReview,
                _ => crate::messaging::QaStatus::Passed,
            };

            let exceptions = qa_response.data.get("exceptions")
                .and_then(|e| e.as_array())
                .map(|arr| arr.iter().filter_map(|v| v.as_str().map(|s| s.to_string())).collect())
                .unwrap_or_default();

            let qa_score = qa_response.data.get("qa_score").unwrap_or(&serde_json::json!(100.0)).as_f64().unwrap_or(100.0);

            crate::messaging::QaVerdict {
                status,
                exceptions,
                qa_score,
            }
        } else {
            crate::messaging::QaVerdict {
                status: crate::messaging::QaStatus::ManualReview,
                exceptions: vec!["QA agent not executed".to_string()],
                qa_score: 50.0,
            }
        }
    }

    /// Calculate estimated cost savings
    /// Estimates the cost savings from automated processing
    fn calculate_cost_savings(&self, processing_time_ms: u64) -> f64 {
        // Assume manual processing takes 30 minutes at $50/hour
        let manual_cost = 25.0;
        // Automated processing cost (minimal)
        let automated_cost = 0.50;
        manual_cost - automated_cost
    }

    /// Create an error result when workflow execution fails
    /// Provides a fallback result with error information for the UI
    async fn create_error_result(&self, request: KycRequest, error_message: String) -> KycResult {
        use crate::messaging::*;
        
        KycResult {
            request_id: request.request_id,
            timestamp: Utc::now(),
            executive_summary: ExecutiveSummary {
                recommendation: Recommendation::Escalate,
                risk_score: 100.0, // High risk due to processing error
                confidence: 0.0,    // No confidence due to error
                processing_time: 0,
                cost_savings: 0.0,
            },
            detailed_analysis: DetailedAnalysis {
                ocr_results: Some(serde_json::json!({"error": "Processing failed", "message": error_message})),
                biometric_results: None,
                watchlist_results: None,
                data_integration_results: None,
                risk_assessment: Some(serde_json::json!({"error": "Unable to assess risk due to processing failure"})),
            },
            audit_trail: AuditTrail {
                processing_steps: vec![],
                data_sources: vec![],
                rules_applied: vec![],
                agent_versions: std::collections::HashMap::new(),
            },
            actionable_insights: ActionableInsights {
                follow_up_actions: vec!["Manual review required due to processing error".to_string()],
                monitoring_requirements: vec!["Monitor system health and Pinecone connectivity".to_string()],
                process_improvements: vec!["Automated processing failed - manual intervention needed".to_string()],
            },
            qa_verdict: QaVerdict {
                status: QaStatus::Failed,
                exceptions: vec!["System processing error".to_string()],
                qa_score: 0.0,
            },
        }
    }

    /// Identify risk factors from agent responses
    /// Extracts specific risk indicators for reporting
    fn identify_risk_factors(&self, responses: &HashMap<String, AgentResponse>) -> Vec<String> {
        let mut risk_factors = Vec::new();

        // OCR risk factors
        if let Some(ocr_response) = responses.get("ocr") {
            if let Some(quality) = ocr_response.data.get("document_quality") {
                if quality.as_f64().unwrap_or(100.0) < 70.0 {
                    risk_factors.push("Poor document quality".to_string());
                }
            }
        }

        // Face recognition risk factors
        if let Some(face_response) = responses.get("face") {
            if let Some(match_score) = face_response.data.get("match_score") {
                if match_score.as_f64().unwrap_or(100.0) < 80.0 {
                    risk_factors.push("Low biometric match confidence".to_string());
                }
            }
        }

        // Watchlist risk factors
        if let Some(watchlist_response) = responses.get("watchlist") {
            if watchlist_response.data.get("flagged").unwrap_or(&serde_json::json!(false)).as_bool().unwrap_or(false) {
                risk_factors.push("Watchlist match detected".to_string());
            }
        }

        risk_factors
    }

    /// Extract data sources from agent responses
    /// Lists all data sources accessed during processing
    fn extract_data_sources(&self, responses: &HashMap<String, AgentResponse>) -> Vec<String> {
        let mut data_sources = vec![
            "Uploaded documents".to_string(),
            "Customer information".to_string(),
        ];

        if responses.contains_key("watchlist") {
            data_sources.push("Sanctions watchlist".to_string());
            data_sources.push("PEP database".to_string());
        }

        if responses.contains_key("data_integration") {
            data_sources.push("External data providers".to_string());
            data_sources.push("Credit bureau".to_string());
        }

        data_sources
    }

    /// Extract rules applied from agent responses
    /// Lists all compliance rules and policies applied
    fn extract_rules_applied(&self, responses: &HashMap<String, AgentResponse>) -> Vec<String> {
        let mut rules = vec![
            "Document authenticity verification".to_string(),
            "Identity verification requirements".to_string(),
            "Data quality standards".to_string(),
        ];

        if responses.contains_key("watchlist") {
            rules.push("AML screening requirements".to_string());
            rules.push("Sanctions compliance".to_string());
        }

        if responses.contains_key("qa") {
            rules.push("Quality assurance policies".to_string());
            rules.push("Risk assessment framework".to_string());
        }

        rules
    }

    /// Generate actionable insights
    /// Provides specific recommendations for follow-up actions
    fn generate_actionable_insights(
        &self,
        responses: &HashMap<String, AgentResponse>,
        risk_score: f64,
    ) -> crate::messaging::ActionableInsights {
        let mut follow_up_actions = Vec::new();
        let mut monitoring_requirements = Vec::new();
        let mut process_improvements = Vec::new();

        // Risk-based follow-up actions
        if risk_score > 60.0 {
            follow_up_actions.push("Escalate to senior compliance officer".to_string());
            follow_up_actions.push("Request additional documentation".to_string());
        } else if risk_score > 40.0 {
            follow_up_actions.push("Enhanced due diligence required".to_string());
            monitoring_requirements.push("Quarterly review recommended".to_string());
        }

        // Agent-specific insights
        if let Some(face_response) = responses.get("face") {
            if face_response.data.get("match_score").unwrap_or(&serde_json::json!(100.0)).as_f64().unwrap_or(100.0) < 80.0 {
                follow_up_actions.push("Manual biometric verification required".to_string());
            }
        }

        if let Some(ocr_response) = responses.get("ocr") {
            if ocr_response.data.get("document_quality").unwrap_or(&serde_json::json!(100.0)).as_f64().unwrap_or(100.0) < 70.0 {
                follow_up_actions.push("Request higher quality document scan".to_string());
                process_improvements.push("Implement document quality pre-check".to_string());
            }
        }

        // General monitoring requirements
        monitoring_requirements.push("Transaction monitoring for 90 days".to_string());
        monitoring_requirements.push("Periodic risk reassessment".to_string());

        // Process improvements
        process_improvements.push("Continuous model training with feedback".to_string());
        process_improvements.push("Regular agent performance review".to_string());

        crate::messaging::ActionableInsights {
            follow_up_actions,
            monitoring_requirements,
            process_improvements,
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_risk_score_calculation() {
        // This would contain comprehensive tests for risk calculation logic
        // Testing various combinations of agent responses
    }

    #[test]
    fn test_recommendation_logic() {
        // This would test the recommendation determination logic
        // With various risk scores and confidence levels
    }
}
