/*!
 * Agentic AI KYC Orchestration Engine
 * Production-grade Rust core for autonomous KYC processing
 */

use actix_web::{web, App, HttpServer, HttpResponse, Result, middleware::Logger};
use actix_cors::Cors;
use actix_files::Files;
use serde::{Deserialize, Serialize};
use std::sync::Arc;
use uuid::Uuid;
use chrono::{DateTime, Utc};
use anyhow::{Result as AnyhowResult, Context};
use tracing::{info, error};
use std::collections::HashMap;
use dashmap::DashMap;

mod config;
mod messaging;
mod orchestrator;
mod agents;
mod database;
mod monitoring;
mod security;
mod ui;

use config::AppConfig;
use messaging::MessageBus;
use orchestrator::KYCOrchestrator;
use database::DatabaseManager;
use monitoring::MetricsCollector;

#[derive(Clone)]
pub struct AppState {
    pub config: Arc<AppConfig>,
    pub message_bus: Arc<MessageBus>,
    pub orchestrator: Arc<KYCOrchestrator>,
    pub database: Arc<DatabaseManager>,
    pub metrics: Arc<MetricsCollector>,
    pub active_sessions: Arc<DashMap<String, KYCSession>>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct KYCSession {
    pub session_id: String,
    pub customer_id: String,
    pub status: SessionStatus,
    pub created_at: DateTime<Utc>,
    pub updated_at: DateTime<Utc>,
    pub current_stage: ProcessingStage,
    pub agent_results: HashMap<String, serde_json::Value>,
    pub final_decision: Option<KYCDecision>,
    pub processing_time: Option<f64>,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub enum SessionStatus {
    Pending,
    Processing,
    Completed,
    Failed,
    RequiresReview,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AgentStatus {
    pub name: String,
    pub status: String,
    pub last_seen: DateTime<Utc>,
    pub health: bool,
    pub last_heartbeat: DateTime<Utc>,
    pub processed_requests: u64,
    pub error_rate: f64,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub enum ProcessingStage {
    DataIngestion,
    QualityValidation,
    KYCAnalysis,
    ComplianceCheck,
    DecisionMaking,
    Completed,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum KYCDecision {
    Approved,
    Rejected,
    RequiresReview,
    RequiresAdditionalInfo,
}

#[derive(Debug, Deserialize, Serialize)]
pub struct KYCProcessRequest {
    pub customer_id: String,
    pub customer_data: serde_json::Value,
    pub priority: Option<String>,
    pub regulatory_requirements: Option<Vec<String>>,
}

#[derive(Debug, Serialize)]
pub struct KYCProcessResponse {
    pub session_id: String,
    pub status: SessionStatus,
    pub message: String,
    pub estimated_completion: Option<DateTime<Utc>>,
}

async fn health_check() -> Result<HttpResponse> {
    Ok(HttpResponse::Ok().json(serde_json::json!({
        "status": "healthy",
        "service": "kyc-orchestrator",
        "timestamp": Utc::now(),
        "version": "1.0.0"
    })))
}

async fn process_kyc(
    data: web::Data<AppState>,
    request: web::Json<KYCProcessRequest>,
) -> Result<HttpResponse> {
    info!("Processing KYC request for customer: {}", request.customer_id);
    
    let session_id = Uuid::new_v4().to_string();
    
    let session = KYCSession {
        session_id: session_id.clone(),
        customer_id: request.customer_id.clone(),
        status: SessionStatus::Pending,
        created_at: Utc::now(),
        updated_at: Utc::now(),
        current_stage: ProcessingStage::DataIngestion,
        agent_results: HashMap::new(),
        final_decision: None,
        processing_time: None,
    };
    
    data.active_sessions.insert(session_id.clone(), session);
    
    let response = KYCProcessResponse {
        session_id: session_id.clone(),
        status: SessionStatus::Processing,
        message: "KYC processing initiated".to_string(),
        estimated_completion: Some(Utc::now() + chrono::Duration::minutes(5)),
    };
    
    Ok(HttpResponse::Ok().json(response))
}

async fn get_session_status(
    data: web::Data<AppState>,
    path: web::Path<String>,
) -> Result<HttpResponse> {
    let session_id = path.into_inner();
    
    match data.active_sessions.get(&session_id) {
        Some(session) => Ok(HttpResponse::Ok().json(&*session)),
        None => Ok(HttpResponse::NotFound().json(serde_json::json!({
            "error": "Session not found",
            "session_id": session_id
        }))),
    }
}

async fn serve_ui() -> Result<HttpResponse> {
    let html = include_str!("ui/templates/index.html");
    Ok(HttpResponse::Ok()
        .content_type("text/html; charset=utf-8")
        .body(html))
}

async fn initialize_app_state() -> AnyhowResult<AppState> {
    eprintln!("DEBUG: Starting app state initialization");
    info!("Initializing application state...");
    
    eprintln!("DEBUG: Loading configuration");
    let config = Arc::new(AppConfig::load().context("Failed to load configuration")?);
    eprintln!("DEBUG: Configuration loaded successfully");
    
    eprintln!("DEBUG: Initializing database");
    let database = Arc::new(DatabaseManager::new(&config.database).await.context("Failed to initialize database")?);
    eprintln!("DEBUG: Database initialized successfully");
    
    eprintln!("DEBUG: Initializing message bus");
    let message_bus = Arc::new(MessageBus::new(&config.kafka).await.context("Failed to initialize message bus")?);
    eprintln!("DEBUG: Message bus initialized successfully");
    
    eprintln!("DEBUG: Initializing metrics");
    let metrics = Arc::new(MetricsCollector::new());
    eprintln!("DEBUG: Metrics initialized successfully");
    
    eprintln!("DEBUG: Initializing orchestrator");
    let orchestrator = Arc::new(KYCOrchestrator::new(config.clone(), message_bus.clone(), database.clone(), metrics.clone()).await.context("Failed to initialize orchestrator")?);
    eprintln!("DEBUG: Orchestrator initialized successfully");
    
    eprintln!("DEBUG: Creating active sessions map");
    let active_sessions = Arc::new(DashMap::new());
    
    Ok(AppState {
        config,
        message_bus,
        orchestrator,
        database,
        metrics,
        active_sessions,
    })
}

#[tokio::main]
async fn main() -> AnyhowResult<()> {
    eprintln!("DEBUG: Starting main function");
    
    // Try to initialize tracing with error handling
    match tracing_subscriber::fmt()
        .with_env_filter(tracing_subscriber::EnvFilter::from_default_env())
        .try_init() {
        Ok(_) => eprintln!("DEBUG: Tracing initialized successfully"),
        Err(e) => eprintln!("DEBUG: Tracing init failed: {}", e),
    }
    
    eprintln!("DEBUG: About to log info message");
    info!("Starting Agentic AI KYC Orchestration Engine...");
    
    eprintln!("DEBUG: About to initialize app state");
    let app_state = match initialize_app_state().await {
        Ok(state) => {
            eprintln!("DEBUG: App state initialized successfully");
            state
        },
        Err(e) => {
            eprintln!("DEBUG: App state initialization failed: {}", e);
            return Err(e);
        }
    };
    let bind_address = format!("{}:{}", 
        app_state.config.server.host, 
        app_state.config.server.port
    );
    
    info!("Server will bind to: {}", bind_address);
    
    HttpServer::new(move || {
        App::new()
            .app_data(web::Data::new(app_state.clone()))
            .wrap(Logger::default())
            .wrap(Cors::default().allow_any_origin().allow_any_method().allow_any_header())
            
            .route("/health", web::get().to(health_check))
            .route("/api/v1/kyc/process", web::post().to(process_kyc))
            .route("/api/v1/kyc/status/{session_id}", web::get().to(get_session_status))
            .route("/", web::get().to(serve_ui))
            
            .service(Files::new("/static", "src/ui/static").show_files_listing())
    })
    .bind(&bind_address)?
    .run()
    .await?;
    
    Ok(())
}