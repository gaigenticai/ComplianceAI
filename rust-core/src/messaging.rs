use rdkafka::config::ClientConfig;
use rdkafka::consumer::{Consumer, StreamConsumer};
use rdkafka::producer::{FutureProducer, FutureRecord};
use rdkafka::Message;
use serde::{Deserialize, Serialize};
use anyhow::Result;
use std::time::Duration;
use uuid::Uuid;
use chrono::{DateTime, Utc};

/// Kafka messaging wrapper for KYC automation platform
/// Handles producer and consumer operations with proper error handling
pub struct KafkaMessaging {
    producer: FutureProducer,
    request_consumer: StreamConsumer,
    result_consumer: StreamConsumer,
    config: crate::config::KafkaConfig,
}

/// KYC request message structure
/// Contains all information needed to process a KYC request
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct KycRequest {
    /// Unique request identifier
    pub request_id: String,
    /// Timestamp when request was created
    pub timestamp: DateTime<Utc>,
    /// Customer information
    pub customer_info: CustomerInfo,
    /// Uploaded document information
    pub documents: Vec<DocumentInfo>,
    /// Processing configuration
    pub processing_config: ProcessingConfig,
}

/// Customer information for KYC processing
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CustomerInfo {
    /// Customer ID (if available)
    pub customer_id: Option<String>,
    /// Customer email
    pub email: Option<String>,
    /// Customer phone number
    pub phone: Option<String>,
    /// Additional metadata
    pub metadata: std::collections::HashMap<String, String>,
}

/// Document information for uploaded files
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DocumentInfo {
    /// Document type (ID, passport, selfie, etc.)
    pub document_type: String,
    /// File path or storage reference
    pub file_path: String,
    /// Original filename
    pub filename: String,
    /// File size in bytes
    pub file_size: u64,
    /// MIME type
    pub mime_type: String,
}

/// Processing configuration for KYC workflow
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ProcessingConfig {
    /// Whether to perform OCR processing
    pub enable_ocr: bool,
    /// Whether to perform face recognition
    pub enable_face_recognition: bool,
    /// Whether to perform watchlist screening
    pub enable_watchlist_screening: bool,
    /// Whether to perform data integration
    pub enable_data_integration: bool,
    /// Whether to perform quality assurance
    pub enable_qa: bool,
    /// Risk tolerance level
    pub risk_tolerance: RiskTolerance,
}

/// Risk tolerance levels for KYC processing
#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum RiskTolerance {
    Low,
    Medium,
    High,
}

/// KYC result message structure
/// Contains comprehensive results from all processing agents
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct KycResult {
    /// Original request ID
    pub request_id: String,
    /// Processing completion timestamp
    pub timestamp: DateTime<Utc>,
    /// Executive summary
    pub executive_summary: ExecutiveSummary,
    /// Detailed analysis from each agent
    pub detailed_analysis: DetailedAnalysis,
    /// Complete audit trail
    pub audit_trail: AuditTrail,
    /// Actionable insights
    pub actionable_insights: ActionableInsights,
    /// QA verdict
    pub qa_verdict: QaVerdict,
}

/// Executive summary with key decision points
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ExecutiveSummary {
    /// Final recommendation
    pub recommendation: Recommendation,
    /// Overall risk score (0-100)
    pub risk_score: f64,
    /// Confidence level (0-100)
    pub confidence: f64,
    /// Total processing time in milliseconds
    pub processing_time: u64,
    /// Estimated cost savings
    pub cost_savings: f64,
}

/// KYC processing recommendations
#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum Recommendation {
    Approve,
    Conditional,
    Escalate,
    Reject,
}

/// Detailed analysis from all agents
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DetailedAnalysis {
    /// OCR extraction results
    pub ocr_results: Option<serde_json::Value>,
    /// Biometric matching results
    pub biometric_results: Option<serde_json::Value>,
    /// Watchlist screening results
    pub watchlist_results: Option<serde_json::Value>,
    /// Data integration results
    pub data_integration_results: Option<serde_json::Value>,
    /// Risk assessment results
    pub risk_assessment: Option<serde_json::Value>,
}

/// Complete audit trail for compliance
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AuditTrail {
    /// Processing steps with timestamps
    pub processing_steps: Vec<ProcessingStep>,
    /// Data sources accessed
    pub data_sources: Vec<String>,
    /// Rules and policies applied
    pub rules_applied: Vec<String>,
    /// Agent versions used
    pub agent_versions: std::collections::HashMap<String, String>,
}

/// Individual processing step in audit trail
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ProcessingStep {
    /// Step name
    pub step_name: String,
    /// Agent responsible
    pub agent: String,
    /// Start timestamp
    pub start_time: DateTime<Utc>,
    /// End timestamp
    pub end_time: DateTime<Utc>,
    /// Step status
    pub status: String,
    /// Additional details
    pub details: serde_json::Value,
}

/// Actionable insights for follow-up
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ActionableInsights {
    /// Required follow-up actions
    pub follow_up_actions: Vec<String>,
    /// Monitoring requirements
    pub monitoring_requirements: Vec<String>,
    /// Process improvement suggestions
    pub process_improvements: Vec<String>,
}

/// Quality assurance verdict
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct QaVerdict {
    /// QA status
    pub status: QaStatus,
    /// Exception details if any
    pub exceptions: Vec<String>,
    /// QA score (0-100)
    pub qa_score: f64,
}

/// QA status enumeration
#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum QaStatus {
    Passed,
    Failed,
    Warning,
    ManualReview,
}

/// Feedback message for continuous learning
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct KycFeedback {
    /// Original request ID
    pub request_id: String,
    /// Feedback timestamp
    pub timestamp: DateTime<Utc>,
    /// Human reviewer ID
    pub reviewer_id: String,
    /// Feedback type
    pub feedback_type: FeedbackType,
    /// Feedback details
    pub feedback: String,
    /// Corrected values if any
    pub corrections: Option<serde_json::Value>,
}

/// Types of feedback for continuous learning
#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum FeedbackType {
    Correction,
    Confirmation,
    Improvement,
    Issue,
}

impl KafkaMessaging {
    /// Create new Kafka messaging instance
    /// Initializes both producer and consumer with proper configuration
    pub fn new(config: crate::config::KafkaConfig) -> Result<Self> {
        // Create producer
        let producer: FutureProducer = ClientConfig::new()
            .set("bootstrap.servers", &config.brokers)
            .set("message.timeout.ms", "5000")
            .set("queue.buffering.max.messages", "10000")
            .create()
            .map_err(|e| anyhow::anyhow!("Failed to create Kafka producer: {}", e))?;

        // Create request consumer (for orchestrator)
        let request_consumer: StreamConsumer = ClientConfig::new()
            .set("group.id", "kyc_orchestrator_requests")
            .set("bootstrap.servers", &config.brokers)
            .set("enable.partition.eof", "false")
            .set("session.timeout.ms", "6000")
            .set("enable.auto.commit", "true")
            .create()
            .map_err(|e| anyhow::anyhow!("Failed to create Kafka request consumer: {}", e))?;

        // Create result consumer (for web interface)
        let result_consumer: StreamConsumer = ClientConfig::new()
            .set("group.id", "kyc_result_consumer")
            .set("bootstrap.servers", &config.brokers)
            .set("enable.partition.eof", "false")
            .set("session.timeout.ms", "6000")
            .set("enable.auto.commit", "true")
            .create()
            .map_err(|e| anyhow::anyhow!("Failed to create Kafka result consumer: {}", e))?;

        Ok(Self {
            producer,
            request_consumer,
            result_consumer,
            config,
        })
    }

    /// Produce a KYC request message to Kafka
    /// Returns the message key for tracking
    pub async fn produce_kyc_request(&self, request: &KycRequest) -> Result<String> {
        let key = request.request_id.clone();
        let payload = serde_json::to_string(request)
            .map_err(|e| anyhow::anyhow!("Failed to serialize KYC request: {}", e))?;

        let record = FutureRecord::to(&self.config.kyc_request_topic)
            .key(&key)
            .payload(&payload);

        self.producer
            .send(record, Duration::from_secs(5))
            .await
            .map_err(|e| anyhow::anyhow!("Failed to send KYC request: {}", e.0))?;

        log::info!("Produced KYC request with ID: {}", key);
        Ok(key)
    }

    /// Produce a KYC result message to Kafka
    /// Returns the message key for tracking
    pub async fn produce_kyc_result(&self, result: &KycResult) -> Result<String> {
        let key = result.request_id.clone();
        let payload = serde_json::to_string(result)
            .map_err(|e| anyhow::anyhow!("Failed to serialize KYC result: {}", e))?;

        let record = FutureRecord::to(&self.config.kyc_result_topic)
            .key(&key)
            .payload(&payload);

        self.producer
            .send(record, Duration::from_secs(5))
            .await
            .map_err(|e| anyhow::anyhow!("Failed to send KYC result: {}", e.0))?;

        log::info!("Produced KYC result with ID: {}", key);
        Ok(key)
    }

    /// Produce feedback message to Kafka
    /// Used for continuous learning and model improvement
    pub async fn produce_feedback(&self, feedback: &KycFeedback) -> Result<String> {
        let key = Uuid::new_v4().to_string();
        let payload = serde_json::to_string(feedback)
            .map_err(|e| anyhow::anyhow!("Failed to serialize feedback: {}", e))?;

        let record = FutureRecord::to(&self.config.kyc_feedback_topic)
            .key(&key)
            .payload(&payload);

        self.producer
            .send(record, Duration::from_secs(5))
            .await
            .map_err(|e| anyhow::anyhow!("Failed to send feedback: {}", e.0))?;

        log::info!("Produced feedback with ID: {}", key);
        Ok(key)
    }

    /// Subscribe to KYC request topic
    /// Used by the orchestrator to process incoming requests
    pub fn subscribe_to_requests(&self) -> Result<()> {
        self.request_consumer
            .subscribe(&[&self.config.kyc_request_topic])
            .map_err(|e| anyhow::anyhow!("Failed to subscribe to requests: {}", e))?;
        
        log::info!("Subscribed to KYC request topic: {}", self.config.kyc_request_topic);
        Ok(())
    }

    /// Subscribe to KYC result topic
    /// Used by the web server to get processing results
    pub fn subscribe_to_results(&self) -> Result<()> {
        self.result_consumer
            .subscribe(&[&self.config.kyc_result_topic])
            .map_err(|e| anyhow::anyhow!("Failed to subscribe to results: {}", e))?;
        
        log::info!("Subscribed to KYC result topic: {}", self.config.kyc_result_topic);
        Ok(())
    }

    /// Get the request consumer reference for message polling
    /// Used by the orchestrator
    pub fn request_consumer(&self) -> &StreamConsumer {
        &self.request_consumer
    }

    /// Get the result consumer reference for message polling
    /// Used by the web server
    pub fn result_consumer(&self) -> &StreamConsumer {
        &self.result_consumer
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_kyc_request_serialization() {
        let request = KycRequest {
            request_id: "test-123".to_string(),
            timestamp: Utc::now(),
            customer_info: CustomerInfo {
                customer_id: Some("cust-456".to_string()),
                email: Some("test@example.com".to_string()),
                phone: Some("+1234567890".to_string()),
                metadata: std::collections::HashMap::new(),
            },
            documents: vec![],
            processing_config: ProcessingConfig {
                enable_ocr: true,
                enable_face_recognition: true,
                enable_watchlist_screening: true,
                enable_data_integration: true,
                enable_qa: true,
                risk_tolerance: RiskTolerance::Medium,
            },
        };

        let serialized = serde_json::to_string(&request).unwrap();
        let deserialized: KycRequest = serde_json::from_str(&serialized).unwrap();
        
        assert_eq!(request.request_id, deserialized.request_id);
    }
}
