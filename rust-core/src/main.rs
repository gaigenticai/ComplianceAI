mod config;
mod messaging;
mod orchestrator;
mod storage;

use actix_files::Files;
use actix_multipart::Multipart;
use actix_web::{
    middleware::Logger, web, App, HttpRequest, HttpResponse, HttpServer, Result as ActixResult,
};
use anyhow::Result;
use chrono::Utc;
use config::Config;
use futures_util::TryStreamExt;
use messaging::{
    CustomerInfo, DocumentInfo, KafkaMessaging, KycFeedback, KycRequest, ProcessingConfig,
    RiskTolerance, FeedbackType,
};
use orchestrator::KycOrchestrator;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::io::Write;
use std::sync::Arc;
use storage::PineconeClient;
use tera::{Context, Tera};
use tokio::sync::RwLock;
use uuid::Uuid;

/// Application state shared across handlers
/// Contains all shared resources and configuration
pub struct AppState {
    /// Application configuration
    pub config: Arc<Config>,
    /// Kafka messaging client
    pub messaging: Arc<KafkaMessaging>,
    /// Pinecone storage client
    pub storage: Arc<PineconeClient>,
    /// Template engine
    pub tera: Tera,
    /// Pending KYC results (request_id -> result)
    pub pending_results: Arc<RwLock<HashMap<String, messaging::KycResult>>>,
}

/// File upload information
#[derive(Debug, Serialize, Deserialize)]
pub struct FileUpload {
    pub filename: String,
    pub content_type: String,
    pub size: usize,
    pub path: String,
}

/// KYC submission form data
#[derive(Debug, Serialize, Deserialize)]
pub struct KycSubmission {
    pub customer_email: Option<String>,
    pub customer_phone: Option<String>,
    pub risk_tolerance: String,
    pub enable_all_checks: bool,
}

/// Feedback submission form data
#[derive(Debug, Serialize, Deserialize)]
pub struct FeedbackSubmission {
    pub request_id: String,
    pub reviewer_id: String,
    pub feedback_type: String,
    pub feedback_text: String,
    pub corrections: Option<String>,
}

#[actix_web::main]
async fn main() -> Result<()> {
    // Initialize logging
    env_logger::init();
    
    // Load environment variables
    dotenv::dotenv().ok();
    
    log::info!("Starting KYC Automation Platform");

    // Load configuration
    let config = Arc::new(Config::load()?);
    log::info!("Configuration loaded successfully");
    log::info!("Server will start on {}:{}", config.server.host, config.server.port);

    // Initialize Kafka messaging
    let messaging = Arc::new(KafkaMessaging::new(config.kafka.clone())?);
    log::info!("Kafka messaging initialized");

    // Initialize Pinecone storage
    let storage = Arc::new(PineconeClient::new(config.pinecone.clone())?);
    log::info!("Pinecone storage initialized");

    // Initialize template engine
    let mut tera = Tera::new("rust-core/src/ui/templates/**/*")?;
    tera.autoescape_on(vec![".html"]);
    log::info!("Template engine initialized");

    // Create application state
    let app_state = web::Data::new(AppState {
        config: config.clone(),
        messaging: messaging.clone(),
        storage: storage.clone(),
        tera,
        pending_results: Arc::new(RwLock::new(HashMap::new())),
    });

    // Start orchestrator in background
    let orchestrator = KycOrchestrator::new(config.clone(), messaging.clone(), storage.clone())?;
    let orchestrator_handle = tokio::spawn(async move {
        if let Err(e) = orchestrator.start().await {
            log::error!("Orchestrator error: {}", e);
        }
    });

    // Start result consumer in background
    let result_consumer_state = app_state.clone();
    let result_consumer_handle = tokio::spawn(async move {
        if let Err(e) = start_result_consumer(result_consumer_state).await {
            log::error!("Result consumer error: {}", e);
        }
    });

    // Start HTTP server
    let server_config = config.clone();
    let server = HttpServer::new(move || {
        App::new()
            .app_data(app_state.clone())
            .wrap(Logger::default())
            .route("/", web::get().to(index_handler))
            .route("/submit", web::post().to(submit_handler))
            .route("/result/{request_id}", web::get().to(result_handler))
            .route("/feedback", web::post().to(feedback_handler))
            .route("/health", web::get().to(health_handler))
            .route("/userguide", web::get().to(userguide_handler))
            .route("/api/stats", web::get().to(stats_handler))
            .service(Files::new("/static", "rust-core/src/ui/static").show_files_listing())
    })
    .bind(format!("{}:{}", server_config.server.host, server_config.server.port))?
    .run();

    log::info!("HTTP server started successfully");

    // Wait for server or background tasks to complete
    tokio::select! {
        result = server => {
            log::info!("HTTP server stopped");
            result?;
        }
        _ = orchestrator_handle => {
            log::info!("Orchestrator stopped");
        }
        _ = result_consumer_handle => {
            log::info!("Result consumer stopped");
        }
    }

    Ok(())
}

/// Home page handler
/// Renders the main KYC submission form
async fn index_handler(data: web::Data<AppState>) -> ActixResult<HttpResponse> {
    let mut context = Context::new();
    context.insert("title", "KYC Automation Platform");
    context.insert("require_auth", &data.config.auth.require_auth);
    
    let html = data.tera.render("index.html", &context)
        .map_err(|e| actix_web::error::ErrorInternalServerError(format!("Template error: {}", e)))?;
    
    Ok(HttpResponse::Ok().content_type("text/html").body(html))
}

/// KYC submission handler
/// Processes uploaded documents and initiates KYC workflow
async fn submit_handler(
    data: web::Data<AppState>,
    mut payload: Multipart,
) -> ActixResult<HttpResponse> {
    let request_id = Uuid::new_v4().to_string();
    let mut documents = Vec::new();
    let mut form_data = HashMap::new();
    
    log::info!("Processing KYC submission: {}", request_id);

    // Process multipart form data
    while let Some(mut field) = payload.try_next().await? {
        let content_disposition = field.content_disposition();
        
        if let Some(name) = content_disposition.get_name() {
            if name.starts_with("file_") {
                // Handle file upload
                if let Some(filename) = content_disposition.get_filename() {
                    let file_path = format!("uploads/{}", Uuid::new_v4());
                    
                    // Create uploads directory if it doesn't exist
                    std::fs::create_dir_all("uploads")?;
                    
                    // Save uploaded file
                    let mut file = std::fs::File::create(&file_path)?;
                    let mut size = 0;
                    
                    while let Some(chunk) = field.try_next().await? {
                        size += chunk.len();
                        if size > data.config.server.max_file_size {
                            return Ok(HttpResponse::BadRequest()
                                .json(serde_json::json!({"error": "File too large"})));
                        }
                        file.write_all(&chunk)?;
                    }
                    
                    // Determine document type from field name
                    let document_type = match name {
                        "file_id" => "id_document",
                        "file_selfie" => "selfie",
                        "file_passport" => "passport",
                        _ => "unknown",
                    };
                    
                    let document_info = DocumentInfo {
                        document_type: document_type.to_string(),
                        file_path,
                        filename: filename.to_string(),
                        file_size: size as u64,
                        mime_type: field.content_type()
                            .map(|ct| ct.to_string())
                            .unwrap_or_else(|| "application/octet-stream".to_string()),
                    };
                    
                    documents.push(document_info);
                    log::info!("Uploaded file: {} ({} bytes)", filename, size);
                }
            } else {
                // Handle form field
                let mut field_data = Vec::new();
                while let Some(chunk) = field.try_next().await? {
                    field_data.extend_from_slice(&chunk);
                }
                
                if let Ok(value) = String::from_utf8(field_data) {
                    form_data.insert(name.to_string(), value);
                }
            }
        }
    }

    // Validate required files
    if documents.is_empty() {
        return Ok(HttpResponse::BadRequest()
            .json(serde_json::json!({"error": "No documents uploaded"})));
    }

    // Create customer info from form data
    let customer_info = CustomerInfo {
        customer_id: None,
        email: form_data.get("customer_email").cloned(),
        phone: form_data.get("customer_phone").cloned(),
        metadata: form_data.clone(),
    };

    // Create processing configuration
    let risk_tolerance = match form_data.get("risk_tolerance").map(|s| s.as_str()).unwrap_or("medium") {
        "low" => RiskTolerance::Low,
        "high" => RiskTolerance::High,
        _ => RiskTolerance::Medium,
    };

    let enable_all = form_data.get("enable_all_checks")
        .map(|s| s == "true" || s == "on")
        .unwrap_or(true);

    let processing_config = ProcessingConfig {
        enable_ocr: enable_all,
        enable_face_recognition: enable_all,
        enable_watchlist_screening: enable_all,
        enable_data_integration: enable_all,
        enable_qa: enable_all,
        risk_tolerance,
    };

    // Create KYC request
    let kyc_request = KycRequest {
        request_id: request_id.clone(),
        timestamp: Utc::now(),
        customer_info,
        documents,
        processing_config,
    };

    // Submit to Kafka for processing
    match data.messaging.produce_kyc_request(&kyc_request).await {
        Ok(_) => {
            log::info!("KYC request submitted successfully: {}", request_id);
            
            // Return JSON response with request ID
            Ok(HttpResponse::Ok().json(serde_json::json!({
                "success": true,
                "request_id": request_id,
                "message": "KYC request submitted successfully",
                "estimated_processing_time": "2-5 minutes"
            })))
        }
        Err(e) => {
            log::error!("Failed to submit KYC request: {}", e);
            Ok(HttpResponse::InternalServerError()
                .json(serde_json::json!({"error": "Failed to submit request"})))
        }
    }
}

/// Result handler
/// Returns KYC processing results for a given request ID
async fn result_handler(
    data: web::Data<AppState>,
    path: web::Path<String>,
) -> ActixResult<HttpResponse> {
    let request_id = path.into_inner();
    
    // Check if result is available
    let results = data.pending_results.read().await;
    if let Some(result) = results.get(&request_id) {
        // Render result page
        let mut context = Context::new();
        context.insert("title", "KYC Results");
        context.insert("result", result);
        context.insert("request_id", &request_id);
        
        let html = data.tera.render("result.html", &context)
            .map_err(|e| actix_web::error::ErrorInternalServerError(format!("Template error: {}", e)))?;
        
        Ok(HttpResponse::Ok().content_type("text/html").body(html))
    } else {
        // Result not ready yet
        let mut context = Context::new();
        context.insert("title", "Processing...");
        context.insert("request_id", &request_id);
        context.insert("message", "Your KYC request is being processed. Please check back in a few minutes.");
        
        let html = data.tera.render("processing.html", &context)
            .map_err(|e| actix_web::error::ErrorInternalServerError(format!("Template error: {}", e)))?;
        
        Ok(HttpResponse::Ok().content_type("text/html").body(html))
    }
}

/// Feedback handler
/// Processes user feedback for continuous learning
async fn feedback_handler(
    data: web::Data<AppState>,
    form: web::Form<FeedbackSubmission>,
) -> ActixResult<HttpResponse> {
    let feedback_type = match form.feedback_type.as_str() {
        "correction" => FeedbackType::Correction,
        "confirmation" => FeedbackType::Confirmation,
        "improvement" => FeedbackType::Improvement,
        _ => FeedbackType::Issue,
    };

    let corrections = form.corrections.as_ref()
        .and_then(|c| serde_json::from_str(c).ok());

    let feedback = KycFeedback {
        request_id: form.request_id.clone(),
        timestamp: Utc::now(),
        reviewer_id: form.reviewer_id.clone(),
        feedback_type,
        feedback: form.feedback_text.clone(),
        corrections,
    };

    match data.messaging.produce_feedback(&feedback).await {
        Ok(_) => {
            log::info!("Feedback submitted for request: {}", form.request_id);
            Ok(HttpResponse::Ok().json(serde_json::json!({
                "success": true,
                "message": "Feedback submitted successfully"
            })))
        }
        Err(e) => {
            log::error!("Failed to submit feedback: {}", e);
            Ok(HttpResponse::InternalServerError()
                .json(serde_json::json!({"error": "Failed to submit feedback"})))
        }
    }
}

/// Health check handler
/// Returns system health status
async fn health_handler(data: web::Data<AppState>) -> ActixResult<HttpResponse> {
    // Check system components
    let mut health_status = serde_json::json!({
        "status": "healthy",
        "timestamp": Utc::now(),
        "components": {
            "web_server": "healthy",
            "kafka": "unknown",
            "pinecone": "unknown"
        }
    });

    // Try to get Pinecone stats to verify connectivity
    match data.storage.get_index_stats().await {
        Ok(_) => {
            health_status["components"]["pinecone"] = serde_json::json!("healthy");
        }
        Err(_) => {
            health_status["components"]["pinecone"] = serde_json::json!("unhealthy");
            health_status["status"] = serde_json::json!("degraded");
        }
    }

    Ok(HttpResponse::Ok().json(health_status))
}

/// User guide handler
/// Renders web-based user documentation
async fn userguide_handler(data: web::Data<AppState>) -> ActixResult<HttpResponse> {
    let mut context = Context::new();
    context.insert("title", "User Guide - KYC Automation Platform");
    
    let html = data.tera.render("userguide.html", &context)
        .map_err(|e| actix_web::error::ErrorInternalServerError(format!("Template error: {}", e)))?;
    
    Ok(HttpResponse::Ok().content_type("text/html").body(html))
}

/// Statistics API handler
/// Returns system statistics and metrics
async fn stats_handler(data: web::Data<AppState>) -> ActixResult<HttpResponse> {
    let results_count = data.pending_results.read().await.len();
    
    let stats = serde_json::json!({
        "pending_results": results_count,
        "uptime": "unknown", // Would implement proper uptime tracking
        "processed_requests": "unknown", // Would implement request counter
        "average_processing_time": "unknown", // Would implement timing metrics
        "system_load": "unknown" // Would implement system monitoring
    });
    
    Ok(HttpResponse::Ok().json(stats))
}

/// Start result consumer
/// Consumes KYC results from Kafka and stores them for web access
async fn start_result_consumer(data: web::Data<AppState>) -> Result<()> {
    log::info!("Starting result consumer");
    
    data.messaging.subscribe_to_results()?;
    
    loop {
        match tokio::time::timeout(
            std::time::Duration::from_secs(1),
            data.messaging.consumer().recv()
        ).await {
            Ok(Ok(msg)) => {
                if let Some(payload) = msg.payload() {
                    match serde_json::from_slice::<messaging::KycResult>(payload) {
                        Ok(result) => {
                            log::info!("Received KYC result: {}", result.request_id);
                            
                            // Store result for web access
                            let mut results = data.pending_results.write().await;
                            results.insert(result.request_id.clone(), result);
                            
                            // Clean up old results (keep only last 1000)
                            if results.len() > 1000 {
                                let oldest_keys: Vec<String> = results.keys()
                                    .take(results.len() - 1000)
                                    .cloned()
                                    .collect();
                                for key in oldest_keys {
                                    results.remove(&key);
                                }
                            }
                        }
                        Err(e) => {
                            log::error!("Failed to parse KYC result: {}", e);
                        }
                    }
                }
            }
            Ok(Err(e)) => {
                log::error!("Kafka consumer error: {}", e);
            }
            Err(_) => {
                // Timeout - continue polling
            }
        }
    }
}
