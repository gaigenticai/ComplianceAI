use serde::{Deserialize, Serialize};
use anyhow::Result;
use std::collections::HashMap;
use uuid::Uuid;
use chrono::{DateTime, Utc};

/// Pinecone vector database client wrapper
/// Handles vector storage and retrieval for KYC data indexing
pub struct PineconeClient {
    client: reqwest::Client,
    config: crate::config::PineconeConfig,
    base_url: String,
}

/// Vector data structure for Pinecone storage
/// Contains embeddings and metadata for KYC records
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct VectorData {
    /// Unique vector ID
    pub id: String,
    /// Vector values (embeddings)
    pub values: Vec<f32>,
    /// Associated metadata
    pub metadata: VectorMetadata,
}

/// Metadata associated with KYC vectors
/// Contains searchable information about KYC records
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct VectorMetadata {
    /// Original KYC request ID
    pub request_id: String,
    /// Customer ID if available
    pub customer_id: Option<String>,
    /// Processing timestamp
    pub timestamp: DateTime<Utc>,
    /// Document types processed
    pub document_types: Vec<String>,
    /// Final recommendation
    pub recommendation: String,
    /// Risk score
    pub risk_score: f64,
    /// Processing status
    pub status: String,
    /// Additional searchable fields
    pub additional_fields: HashMap<String, String>,
}

/// Query request for vector similarity search
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct QueryRequest {
    /// Query vector
    pub vector: Vec<f32>,
    /// Number of results to return
    pub top_k: usize,
    /// Include metadata in results
    pub include_metadata: bool,
    /// Include vector values in results
    pub include_values: bool,
    /// Metadata filter
    pub filter: Option<HashMap<String, serde_json::Value>>,
}

/// Query response from vector similarity search
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct QueryResponse {
    /// Matching vectors with scores
    pub matches: Vec<VectorMatch>,
    /// Query execution statistics
    pub stats: QueryStats,
}

/// Individual vector match from query
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct VectorMatch {
    /// Vector ID
    pub id: String,
    /// Similarity score
    pub score: f64,
    /// Vector values (if requested)
    pub values: Option<Vec<f32>>,
    /// Vector metadata (if requested)
    pub metadata: Option<VectorMetadata>,
}

/// Query execution statistics
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct QueryStats {
    /// Number of vectors searched
    pub vectors_searched: usize,
    /// Query execution time in milliseconds
    pub execution_time_ms: u64,
}

/// Upsert request for inserting/updating vectors
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct UpsertRequest {
    /// Vectors to upsert
    pub vectors: Vec<VectorData>,
    /// Namespace (optional)
    pub namespace: Option<String>,
}

/// Upsert response
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct UpsertResponse {
    /// Number of vectors upserted
    pub upserted_count: usize,
}

/// Delete request for removing vectors
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DeleteRequest {
    /// Vector IDs to delete
    pub ids: Vec<String>,
    /// Namespace (optional)
    pub namespace: Option<String>,
}

impl PineconeClient {
    /// Create new Pinecone client instance
    /// Configures HTTP client for vector database operations
    pub fn new(config: crate::config::PineconeConfig) -> Result<Self> {
        let client = reqwest::Client::builder()
            .timeout(std::time::Duration::from_secs(30))
            .build()
            .map_err(|e| anyhow::anyhow!("Failed to create HTTP client: {}", e))?;

        // Construct base URL based on environment
        let base_url = if config.environment == "local" {
            // Local Pinecone emulator
            format!("http://localhost:8080")
        } else {
            // Pinecone cloud service
            format!("https://{}-{}.svc.{}.pinecone.io", 
                config.index_name, 
                "project-id", // This would be configurable in production
                config.environment
            )
        };

        Ok(Self {
            client,
            config,
            base_url,
        })
    }

    /// Upsert vectors to Pinecone index
    /// Inserts or updates KYC record vectors for similarity search
    pub async fn upsert_vectors(&self, vectors: Vec<VectorData>) -> Result<UpsertResponse> {
        let url = format!("{}/vectors/upsert", self.base_url);
        
        let request = UpsertRequest {
            vectors,
            namespace: None,
        };

        let response = self.client
            .post(&url)
            .header("Api-Key", &self.config.api_key)
            .header("Content-Type", "application/json")
            .json(&request)
            .send()
            .await
            .map_err(|e| anyhow::anyhow!("Failed to send upsert request: {}", e))?;

        if !response.status().is_success() {
            let error_text = response.text().await.unwrap_or_default();
            return Err(anyhow::anyhow!("Upsert failed: {}", error_text));
        }

        let upsert_response: UpsertResponse = response
            .json()
            .await
            .map_err(|e| anyhow::anyhow!("Failed to parse upsert response: {}", e))?;

        log::info!("Successfully upserted {} vectors", upsert_response.upserted_count);
        Ok(upsert_response)
    }

    /// Query vectors by similarity
    /// Finds similar KYC records based on vector embeddings
    pub async fn query_vectors(&self, query: QueryRequest) -> Result<QueryResponse> {
        let url = format!("{}/query", self.base_url);

        let response = self.client
            .post(&url)
            .header("Api-Key", &self.config.api_key)
            .header("Content-Type", "application/json")
            .json(&query)
            .send()
            .await
            .map_err(|e| anyhow::anyhow!("Failed to send query request: {}", e))?;

        if !response.status().is_success() {
            let error_text = response.text().await.unwrap_or_default();
            return Err(anyhow::anyhow!("Query failed: {}", error_text));
        }

        let query_response: QueryResponse = response
            .json()
            .await
            .map_err(|e| anyhow::anyhow!("Failed to parse query response: {}", e))?;

        log::info!("Query returned {} matches", query_response.matches.len());
        Ok(query_response)
    }

    /// Delete vectors from index
    /// Removes KYC records from vector database
    pub async fn delete_vectors(&self, ids: Vec<String>) -> Result<()> {
        let url = format!("{}/vectors/delete", self.base_url);
        
        let request = DeleteRequest {
            ids: ids.clone(),
            namespace: None,
        };

        let response = self.client
            .post(&url)
            .header("Api-Key", &self.config.api_key)
            .header("Content-Type", "application/json")
            .json(&request)
            .send()
            .await
            .map_err(|e| anyhow::anyhow!("Failed to send delete request: {}", e))?;

        if !response.status().is_success() {
            let error_text = response.text().await.unwrap_or_default();
            return Err(anyhow::anyhow!("Delete failed: {}", error_text));
        }

        log::info!("Successfully deleted {} vectors", ids.len());
        Ok(())
    }

    /// Store KYC result in vector database
    /// Converts KYC result to vector format and stores for future similarity searches
    pub async fn store_kyc_result(&self, result: &crate::messaging::KycResult) -> Result<String> {
        // Generate embedding vector from KYC result
        // In production, this would use a proper embedding model
        let embedding = self.generate_embedding_from_result(result)?;
        
        let vector_id = Uuid::new_v4().to_string();
        let vector_data = VectorData {
            id: vector_id.clone(),
            values: embedding,
            metadata: VectorMetadata {
                request_id: result.request_id.clone(),
                customer_id: None, // Would extract from result if available
                timestamp: result.timestamp,
                document_types: vec![], // Would extract from result
                recommendation: format!("{:?}", result.executive_summary.recommendation),
                risk_score: result.executive_summary.risk_score,
                status: "completed".to_string(),
                additional_fields: HashMap::new(),
            },
        };

        self.upsert_vectors(vec![vector_data]).await?;
        Ok(vector_id)
    }

    /// Find similar KYC cases
    /// Searches for similar historical cases based on current processing results
    pub async fn find_similar_cases(&self, result: &crate::messaging::KycResult, limit: usize) -> Result<Vec<VectorMatch>> {
        let embedding = self.generate_embedding_from_result(result)?;
        
        let query = QueryRequest {
            vector: embedding,
            top_k: limit,
            include_metadata: true,
            include_values: false,
            filter: None,
        };

        let response = self.query_vectors(query).await?;
        Ok(response.matches)
    }

    /// Generate embedding vector from KYC result
    /// This is a simplified implementation - in production would use proper ML models
    fn generate_embedding_from_result(&self, result: &crate::messaging::KycResult) -> Result<Vec<f32>> {
        // Simplified embedding generation based on key features
        // In production, this would use transformer models or specialized embeddings
        let mut embedding = vec![0.0; self.config.dimension];
        
        // Risk score component
        embedding[0] = result.executive_summary.risk_score as f32 / 100.0;
        
        // Confidence component
        embedding[1] = result.executive_summary.confidence as f32 / 100.0;
        
        // Recommendation component (one-hot encoding)
        match result.executive_summary.recommendation {
            crate::messaging::Recommendation::Approve => embedding[2] = 1.0,
            crate::messaging::Recommendation::Conditional => embedding[3] = 1.0,
            crate::messaging::Recommendation::Escalate => embedding[4] = 1.0,
            crate::messaging::Recommendation::Reject => embedding[5] = 1.0,
        }
        
        // QA score component
        embedding[6] = result.qa_verdict.qa_score as f32 / 100.0;
        
        // Fill remaining dimensions with normalized random values based on content hash
        let content_hash = self.hash_result_content(result);
        for i in 7..embedding.len() {
            embedding[i] = ((content_hash.wrapping_mul(i as u64) % 1000) as f32) / 1000.0;
        }
        
        Ok(embedding)
    }

    /// Generate deterministic hash from result content
    /// Used for consistent embedding generation
    fn hash_result_content(&self, result: &crate::messaging::KycResult) -> u64 {
        use std::collections::hash_map::DefaultHasher;
        use std::hash::{Hash, Hasher};
        
        let mut hasher = DefaultHasher::new();
        result.request_id.hash(&mut hasher);
        result.executive_summary.risk_score.to_bits().hash(&mut hasher);
        result.executive_summary.confidence.to_bits().hash(&mut hasher);
        hasher.finish()
    }

    /// Get index statistics
    /// Returns information about the vector index
    pub async fn get_index_stats(&self) -> Result<serde_json::Value> {
        let url = format!("{}/describe_index_stats", self.base_url);

        let response = self.client
            .post(&url)
            .header("Api-Key", &self.config.api_key)
            .header("Content-Type", "application/json")
            .send()
            .await
            .map_err(|e| anyhow::anyhow!("Failed to get index stats: {}", e))?;

        if !response.status().is_success() {
            let error_text = response.text().await.unwrap_or_default();
            return Err(anyhow::anyhow!("Get stats failed: {}", error_text));
        }

        let stats: serde_json::Value = response
            .json()
            .await
            .map_err(|e| anyhow::anyhow!("Failed to parse stats response: {}", e))?;

        Ok(stats)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::messaging::*;

    #[test]
    fn test_vector_metadata_serialization() {
        let metadata = VectorMetadata {
            request_id: "test-123".to_string(),
            customer_id: Some("cust-456".to_string()),
            timestamp: Utc::now(),
            document_types: vec!["passport".to_string(), "selfie".to_string()],
            recommendation: "Approve".to_string(),
            risk_score: 25.5,
            status: "completed".to_string(),
            additional_fields: HashMap::new(),
        };

        let serialized = serde_json::to_string(&metadata).unwrap();
        let deserialized: VectorMetadata = serde_json::from_str(&serialized).unwrap();
        
        assert_eq!(metadata.request_id, deserialized.request_id);
        assert_eq!(metadata.risk_score, deserialized.risk_score);
    }

    #[test]
    fn test_embedding_generation() {
        let config = crate::config::PineconeConfig {
            api_key: "test".to_string(),
            environment: "test".to_string(),
            index_name: "test".to_string(),
            dimension: 128,
        };
        
        let client = PineconeClient::new(config).unwrap();
        
        let result = KycResult {
            request_id: "test-123".to_string(),
            timestamp: Utc::now(),
            executive_summary: ExecutiveSummary {
                recommendation: Recommendation::Approve,
                risk_score: 25.0,
                confidence: 95.0,
                processing_time: 1000,
                cost_savings: 100.0,
            },
            detailed_analysis: DetailedAnalysis {
                ocr_results: None,
                biometric_results: None,
                watchlist_results: None,
                data_integration_results: None,
                risk_assessment: None,
            },
            audit_trail: AuditTrail {
                processing_steps: vec![],
                data_sources: vec![],
                rules_applied: vec![],
                agent_versions: HashMap::new(),
            },
            actionable_insights: ActionableInsights {
                follow_up_actions: vec![],
                monitoring_requirements: vec![],
                process_improvements: vec![],
            },
            qa_verdict: QaVerdict {
                status: QaStatus::Passed,
                exceptions: vec![],
                qa_score: 98.0,
            },
        };
        
        let embedding = client.generate_embedding_from_result(&result).unwrap();
        assert_eq!(embedding.len(), 128);
        assert_eq!(embedding[0], 0.25); // Risk score normalized
        assert_eq!(embedding[1], 0.95); // Confidence normalized
        assert_eq!(embedding[2], 1.0);  // Approve recommendation
    }
}
