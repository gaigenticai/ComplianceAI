/*!
 * Database Manager
 * Handles PostgreSQL and MongoDB connections
 */

use anyhow::{Result, Context};
use sqlx::{PgPool, Row};
use mongodb::{Client as MongoClient, Database};
use serde_json::Value;
use tracing::{info, error};

use crate::{config::DatabaseConfig, orchestrator::KYCResult, KYCSession};

pub struct DatabaseManager {
    pg_pool: PgPool,
    mongo_db: Database,
}

impl DatabaseManager {
    pub async fn new(config: &DatabaseConfig) -> Result<Self> {
        info!("Initializing database connections...");
        
        // Initialize PostgreSQL connection with proper pool settings
        let pg_pool = sqlx::postgres::PgPoolOptions::new()
            .max_connections(config.max_connections)
            .acquire_timeout(std::time::Duration::from_secs(config.connection_timeout))
            .idle_timeout(std::time::Duration::from_secs(600))
            .connect(&config.postgres_url)
            .await
            .context("Failed to connect to PostgreSQL")?;
        
        // Run migrations
        sqlx::migrate!("./migrations")
            .run(&pg_pool)
            .await
            .context("Failed to run database migrations")?;
        
        // Initialize MongoDB connection
        let mongo_client = MongoClient::with_uri_str(&config.mongodb_url)
            .await
            .context("Failed to connect to MongoDB")?;
        
        let mongo_db = mongo_client.database("kyc_db");
        
        info!("Database connections initialized successfully");
        
        Ok(Self {
            pg_pool,
            mongo_db,
        })
    }
    
    pub async fn store_kyc_result(&self, result: &KYCResult) -> Result<()> {
        let query = r#"
            INSERT INTO kyc_results (
                session_id, customer_id, decision, confidence_score, 
                processing_time, agent_results, compliance_status, 
                risk_score, recommendations, completed_at
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
            ON CONFLICT (session_id) DO UPDATE SET
                decision = EXCLUDED.decision,
                confidence_score = EXCLUDED.confidence_score,
                processing_time = EXCLUDED.processing_time,
                agent_results = EXCLUDED.agent_results,
                compliance_status = EXCLUDED.compliance_status,
                risk_score = EXCLUDED.risk_score,
                recommendations = EXCLUDED.recommendations,
                completed_at = EXCLUDED.completed_at
        "#;
        
        let decision_str = match result.decision {
            crate::KYCDecision::Approved => "approved",
            crate::KYCDecision::Rejected => "rejected",
            crate::KYCDecision::RequiresReview => "requires_review",
            crate::KYCDecision::RequiresAdditionalInfo => "requires_additional_info",
        };
        
        let agent_results_json = serde_json::to_value(&result.agent_results)?;
        let recommendations_json = serde_json::to_value(&result.recommendations)?;
        
        sqlx::query(query)
            .bind(&result.session_id)
            .bind(&result.customer_id)
            .bind(decision_str)
            .bind(result.confidence_score)
            .bind(result.processing_time)
            .bind(&agent_results_json)
            .bind(&result.compliance_status)
            .bind(result.risk_score)
            .bind(&recommendations_json)
            .bind(result.completed_at)
            .execute(&self.pg_pool)
            .await
            .context("Failed to store KYC result")?;
        
        Ok(())
    }
    
    pub async fn get_session(&self, session_id: &str) -> Result<Option<KYCSession>> {
        let query = r#"
            SELECT session_id, customer_id, decision, confidence_score, 
                   processing_time, agent_results, compliance_status, 
                   risk_score, recommendations, completed_at
            FROM kyc_results 
            WHERE session_id = $1
        "#;
        
        match sqlx::query(query)
            .bind(session_id)
            .fetch_optional(&self.pg_pool)
            .await?
        {
            Some(row) => {
                let agent_results: Value = row.get("agent_results");
                let agent_results_map: std::collections::HashMap<String, Value> = 
                    serde_json::from_value(agent_results)?;
                
                let decision_str: String = row.get("decision");
                let decision = match decision_str.as_str() {
                    "approved" => crate::KYCDecision::Approved,
                    "rejected" => crate::KYCDecision::Rejected,
                    "requires_additional_info" => crate::KYCDecision::RequiresAdditionalInfo,
                    _ => crate::KYCDecision::RequiresReview,
                };
                
                let session = KYCSession {
                    session_id: row.get("session_id"),
                    customer_id: row.get("customer_id"),
                    status: crate::SessionStatus::Completed,
                    created_at: row.get("completed_at"), // Using completed_at as created_at
                    updated_at: row.get("completed_at"),
                    current_stage: crate::ProcessingStage::Completed,
                    agent_results: agent_results_map,
                    final_decision: Some(decision),
                    processing_time: Some(row.get("processing_time")),
                };
                
                Ok(Some(session))
            }
            None => Ok(None),
        }
    }
    
    pub async fn store_customer_data(&self, customer_id: &str, data: &Value) -> Result<()> {
        let collection = self.mongo_db.collection::<mongodb::bson::Document>("customers");
        
        let doc = mongodb::bson::to_document(&serde_json::json!({
            "customer_id": customer_id,
            "data": data,
            "created_at": chrono::Utc::now(),
            "updated_at": chrono::Utc::now()
        }))?;
        
        collection.insert_one(doc, None).await
            .context("Failed to store customer data")?;
        
        Ok(())
    }
    
    pub async fn get_customer_data(&self, customer_id: &str) -> Result<Option<Value>> {
        let collection = self.mongo_db.collection::<mongodb::bson::Document>("customers");
        
        let filter = mongodb::bson::doc! { "customer_id": customer_id };
        
        match collection.find_one(filter, None).await? {
            Some(doc) => {
                let data = doc.get("data")
                    .and_then(|v| mongodb::bson::from_bson(v.clone()).ok())
                    .unwrap_or(Value::Null);
                Ok(Some(data))
            }
            None => Ok(None),
        }
    }
    
    pub async fn health_check(&self) -> Result<bool> {
        // Check PostgreSQL
        match sqlx::query("SELECT 1").fetch_one(&self.pg_pool).await {
            Ok(_) => {},
            Err(e) => {
                error!("PostgreSQL health check failed: {}", e);
                return Ok(false);
            }
        }
        
        // Check MongoDB
        match self.mongo_db.run_command(mongodb::bson::doc! { "ping": 1 }, None).await {
            Ok(_) => {},
            Err(e) => {
                error!("MongoDB health check failed: {}", e);
                return Ok(false);
            }
        }
        
        Ok(true)
    }
}
