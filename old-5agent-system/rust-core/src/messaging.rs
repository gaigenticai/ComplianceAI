/*!
 * Message Bus Implementation
 * Kafka-based messaging for inter-agent communication
 */

use rdkafka::{
    producer::{FutureProducer, FutureRecord, Producer},
    consumer::{Consumer, StreamConsumer},
    config::ClientConfig,
    Message,
};
use serde::{Deserialize, Serialize};
use anyhow::{Result, Context};
use tracing::{info, error, debug};
use std::time::Duration;
use tokio::time::timeout;

use crate::config::KafkaConfig;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AgentMessage {
    pub message_id: String,
    pub agent_name: String,
    pub message_type: MessageType,
    pub payload: serde_json::Value,
    pub timestamp: chrono::DateTime<chrono::Utc>,
    pub correlation_id: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum MessageType {
    DataIngestionRequest,
    DataIngestionResponse,
    KYCAnalysisRequest,
    KYCAnalysisResponse,
    DecisionRequest,
    DecisionResponse,
    ComplianceCheckRequest,
    ComplianceCheckResponse,
    QualityCheckRequest,
    QualityCheckResponse,
    Notification,
    HealthCheck,
}

pub struct MessageBus {
    producer: FutureProducer,
    consumer: StreamConsumer,
    config: KafkaConfig,
}

impl MessageBus {
    pub async fn new(config: &KafkaConfig) -> Result<Self> {
        info!("Initializing Kafka message bus...");
        
        // Create producer
        let producer: FutureProducer = ClientConfig::new()
            .set("bootstrap.servers", &config.bootstrap_servers)
            .set("acks", &config.producer_config.acks)
            .set("retries", &config.producer_config.retries.to_string())
            .set("batch.size", &config.producer_config.batch_size.to_string())
            .set("linger.ms", &config.producer_config.linger_ms.to_string())
            .set("compression.type", "snappy")
            .set("max.in.flight.requests.per.connection", "1")
            .create()
            .context("Failed to create Kafka producer")?;
        
        // Create consumer
        let consumer: StreamConsumer = ClientConfig::new()
            .set("bootstrap.servers", &config.bootstrap_servers)
            .set("group.id", &config.group_id)
            .set("auto.offset.reset", &config.consumer_config.auto_offset_reset)
            .set("enable.auto.commit", &config.consumer_config.enable_auto_commit.to_string())
            .set("session.timeout.ms", &config.consumer_config.session_timeout_ms.to_string())
            .create()
            .context("Failed to create Kafka consumer")?;
        
        // Subscribe to topics
        let topics = vec![
            config.topics.data_ingestion.as_str(),
            config.topics.kyc_analysis.as_str(),
            config.topics.decision_results.as_str(),
            config.topics.compliance_results.as_str(),
            config.topics.quality_results.as_str(),
            config.topics.notifications.as_str(),
        ];
        
        consumer.subscribe(&topics)
            .context("Failed to subscribe to Kafka topics")?;
        
        info!("Kafka message bus initialized successfully");
        
        Ok(Self {
            producer,
            consumer,
            config: config.clone(),
        })
    }
    
    pub async fn publish_message(&self, topic: &str, message: &AgentMessage) -> Result<()> {
        debug!("Publishing message to topic: {}", topic);
        
        let payload = serde_json::to_string(message)
            .context("Failed to serialize message")?;
        
        let record = FutureRecord::to(topic)
            .key(&message.message_id)
            .payload(&payload);
        
        let delivery_timeout = Duration::from_secs(30);
        
        match timeout(delivery_timeout, self.producer.send(record, Duration::from_secs(0))).await {
            Ok(Ok((partition, offset))) => {
                debug!("Message published successfully to partition {} at offset {}", partition, offset);
                Ok(())
            }
            Ok(Err((kafka_error, _))) => {
                error!("Failed to publish message: {}", kafka_error);
                Err(anyhow::anyhow!("Kafka publish error: {}", kafka_error))
            }
            Err(_) => {
                error!("Message publish timeout");
                Err(anyhow::anyhow!("Message publish timeout"))
            }
        }
    }
    
    pub async fn publish_data_ingestion_request(&self, session_id: &str, customer_data: serde_json::Value) -> Result<()> {
        let message = AgentMessage {
            message_id: uuid::Uuid::new_v4().to_string(),
            agent_name: "orchestrator".to_string(),
            message_type: MessageType::DataIngestionRequest,
            payload: serde_json::json!({
                "session_id": session_id,
                "customer_data": customer_data
            }),
            timestamp: chrono::Utc::now(),
            correlation_id: Some(session_id.to_string()),
        };
        
        self.publish_message(&self.config.topics.data_ingestion, &message).await
    }
    
    pub async fn publish_kyc_analysis_request(&self, session_id: &str, ingested_data: serde_json::Value) -> Result<()> {
        let message = AgentMessage {
            message_id: uuid::Uuid::new_v4().to_string(),
            agent_name: "orchestrator".to_string(),
            message_type: MessageType::KYCAnalysisRequest,
            payload: serde_json::json!({
                "session_id": session_id,
                "ingested_data": ingested_data
            }),
            timestamp: chrono::Utc::now(),
            correlation_id: Some(session_id.to_string()),
        };
        
        self.publish_message(&self.config.topics.kyc_analysis, &message).await
    }
    
    pub async fn publish_decision_request(&self, session_id: &str, analysis_results: serde_json::Value) -> Result<()> {
        let message = AgentMessage {
            message_id: uuid::Uuid::new_v4().to_string(),
            agent_name: "orchestrator".to_string(),
            message_type: MessageType::DecisionRequest,
            payload: serde_json::json!({
                "session_id": session_id,
                "analysis_results": analysis_results
            }),
            timestamp: chrono::Utc::now(),
            correlation_id: Some(session_id.to_string()),
        };
        
        self.publish_message(&self.config.topics.decision_results, &message).await
    }
    
    pub async fn publish_compliance_check_request(&self, session_id: &str, customer_data: serde_json::Value) -> Result<()> {
        let message = AgentMessage {
            message_id: uuid::Uuid::new_v4().to_string(),
            agent_name: "orchestrator".to_string(),
            message_type: MessageType::ComplianceCheckRequest,
            payload: serde_json::json!({
                "session_id": session_id,
                "customer_data": customer_data
            }),
            timestamp: chrono::Utc::now(),
            correlation_id: Some(session_id.to_string()),
        };
        
        self.publish_message(&self.config.topics.compliance_results, &message).await
    }
    
    pub async fn publish_quality_check_request(&self, session_id: &str, customer_data: serde_json::Value) -> Result<()> {
        let message = AgentMessage {
            message_id: uuid::Uuid::new_v4().to_string(),
            agent_name: "orchestrator".to_string(),
            message_type: MessageType::QualityCheckRequest,
            payload: serde_json::json!({
                "session_id": session_id,
                "customer_data": customer_data
            }),
            timestamp: chrono::Utc::now(),
            correlation_id: Some(session_id.to_string()),
        };
        
        self.publish_message(&self.config.topics.quality_results, &message).await
    }
    
    pub async fn publish_completion_notification(&self, session_id: &str, result: &crate::orchestrator::KYCResult) -> Result<()> {
        let message = AgentMessage {
            message_id: uuid::Uuid::new_v4().to_string(),
            agent_name: "orchestrator".to_string(),
            message_type: MessageType::Notification,
            payload: serde_json::json!({
                "session_id": session_id,
                "notification_type": "kyc_completed",
                "result": result
            }),
            timestamp: chrono::Utc::now(),
            correlation_id: Some(session_id.to_string()),
        };
        
        self.publish_message(&self.config.topics.notifications, &message).await
    }
    
    pub async fn consume_messages<F>(&self, mut handler: F) -> Result<()>
    where
        F: FnMut(AgentMessage) -> Result<()>,
    {
        info!("Starting message consumption...");
        
        loop {
            match self.consumer.recv().await {
                Ok(message) => {
                    if let Some(payload) = message.payload() {
                        match serde_json::from_slice::<AgentMessage>(payload) {
                            Ok(agent_message) => {
                                debug!("Received message: {:?}", agent_message.message_type);
                                
                                if let Err(e) = handler(agent_message) {
                                    error!("Message handler error: {}", e);
                                }
                            }
                            Err(e) => {
                                error!("Failed to deserialize message: {}", e);
                            }
                        }
                    }
                }
                Err(e) => {
                    error!("Kafka consumer error: {}", e);
                    tokio::time::sleep(Duration::from_secs(1)).await;
                }
            }
        }
    }
    
    pub async fn health_check(&self) -> Result<bool> {
        // Simple health check by trying to get metadata
        match self.producer.client().fetch_metadata(None, Duration::from_secs(5)) {
            Ok(_) => Ok(true),
            Err(e) => {
                error!("Kafka health check failed: {}", e);
                Ok(false)
            }
        }
    }
}
