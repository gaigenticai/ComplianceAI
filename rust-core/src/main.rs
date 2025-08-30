mod config;
mod messaging;
mod orchestrator;
mod storage;

use actix_files::Files;
use actix_multipart::Multipart;
use actix_web::{
    middleware::Logger, web, App, HttpRequest, HttpResponse, HttpServer, Result as ActixResult,
    dev::{ServiceRequest, ServiceResponse, Transform, Service},
    Error,
};
use std::pin::Pin;
use std::task::{Context as TaskContext, Poll};
use std::future::Future;
use anyhow::Result;
use chrono::Utc;
use config::Config;
use futures_util::{StreamExt, TryStreamExt};
use rdkafka::Message;
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
    /// Application metrics
    pub metrics: Arc<RwLock<AppMetrics>>,
}

/// Application metrics for monitoring and observability
#[derive(Debug, Clone)]
pub struct AppMetrics {
    /// Application start time
    pub start_time: std::time::Instant,
    /// Total number of processed requests
    pub total_requests: u64,
    /// Total number of successful requests
    pub successful_requests: u64,
    /// Total number of failed requests
    pub failed_requests: u64,
    /// Processing times for calculating averages (last 1000 requests)
    pub processing_times: std::collections::VecDeque<u64>,
    /// Current system load metrics
    pub system_load: SystemLoad,
    /// Request counts by endpoint
    pub endpoint_counts: HashMap<String, u64>,
    /// Error counts by type
    pub error_counts: HashMap<String, u64>,
}

/// System load metrics
#[derive(Debug, Clone)]
pub struct SystemLoad {
    /// CPU usage percentage
    pub cpu_usage: f64,
    /// Memory usage in bytes
    pub memory_usage: u64,
    /// Total memory in bytes
    pub total_memory: u64,
    /// Disk usage percentage
    pub disk_usage: f64,
    /// Network bytes received
    pub network_rx_bytes: u64,
    /// Network bytes transmitted
    pub network_tx_bytes: u64,
    /// Last updated timestamp
    pub last_updated: std::time::Instant,
}

impl Default for AppMetrics {
    fn default() -> Self {
        Self {
            start_time: std::time::Instant::now(),
            total_requests: 0,
            successful_requests: 0,
            failed_requests: 0,
            processing_times: std::collections::VecDeque::with_capacity(1000),
            system_load: SystemLoad::default(),
            endpoint_counts: HashMap::new(),
            error_counts: HashMap::new(),
        }
    }
}

impl Default for SystemLoad {
    fn default() -> Self {
        Self {
            cpu_usage: 0.0,
            memory_usage: 0,
            total_memory: 0,
            disk_usage: 0.0,
            network_rx_bytes: 0,
            network_tx_bytes: 0,
            last_updated: std::time::Instant::now(),
        }
    }
}

impl AppMetrics {
    /// Record a new request
    pub fn record_request(&mut self, endpoint: &str, processing_time_ms: u64, success: bool) {
        self.total_requests += 1;
        
        if success {
            self.successful_requests += 1;
        } else {
            self.failed_requests += 1;
        }
        
        // Track processing time (keep only last 1000)
        if self.processing_times.len() >= 1000 {
            self.processing_times.pop_front();
        }
        self.processing_times.push_back(processing_time_ms);
        
        // Track endpoint usage
        *self.endpoint_counts.entry(endpoint.to_string()).or_insert(0) += 1;
    }
    
    /// Record an error
    pub fn record_error(&mut self, error_type: &str) {
        *self.error_counts.entry(error_type.to_string()).or_insert(0) += 1;
    }
    
    /// Get average processing time
    pub fn average_processing_time(&self) -> f64 {
        if self.processing_times.is_empty() {
            0.0
        } else {
            let sum: u64 = self.processing_times.iter().sum();
            sum as f64 / self.processing_times.len() as f64
        }
    }
    
    /// Get uptime in seconds
    pub fn uptime_seconds(&self) -> u64 {
        self.start_time.elapsed().as_secs()
    }
    
    /// Update system load metrics
    pub fn update_system_load(&mut self) {
        // Update system metrics if it's been more than 30 seconds
        if self.system_load.last_updated.elapsed().as_secs() >= 30 {
            self.system_load = Self::collect_system_metrics();
        }
    }
    
    /// Collect current system metrics
    fn collect_system_metrics() -> SystemLoad {
        use std::fs;
        
        let mut load = SystemLoad::default();
        load.last_updated = std::time::Instant::now();
        
        // Collect CPU usage from /proc/stat (Linux)
        if let Ok(stat_content) = fs::read_to_string("/proc/stat") {
            if let Some(cpu_line) = stat_content.lines().next() {
                if let Some(cpu_usage) = Self::parse_cpu_usage(cpu_line) {
                    load.cpu_usage = cpu_usage;
                }
            }
        }
        
        // Collect memory usage from /proc/meminfo (Linux)
        if let Ok(meminfo_content) = fs::read_to_string("/proc/meminfo") {
            let (total, available) = Self::parse_memory_info(&meminfo_content);
            load.total_memory = total;
            load.memory_usage = total.saturating_sub(available);
        }
        
        // Collect disk usage from /proc/diskstats (Linux)
        if let Ok(diskstats_content) = fs::read_to_string("/proc/diskstats") {
            load.disk_usage = Self::parse_disk_usage(&diskstats_content);
        }
        
        // Collect network stats from /proc/net/dev (Linux)
        if let Ok(netdev_content) = fs::read_to_string("/proc/net/dev") {
            let (rx_bytes, tx_bytes) = Self::parse_network_stats(&netdev_content);
            load.network_rx_bytes = rx_bytes;
            load.network_tx_bytes = tx_bytes;
        }
        
        load
    }
    
    /// Parse CPU usage from /proc/stat
    fn parse_cpu_usage(cpu_line: &str) -> Option<f64> {
        let parts: Vec<&str> = cpu_line.split_whitespace().collect();
        if parts.len() >= 8 && parts[0] == "cpu" {
            let user: u64 = parts[1].parse().ok()?;
            let nice: u64 = parts[2].parse().ok()?;
            let system: u64 = parts[3].parse().ok()?;
            let idle: u64 = parts[4].parse().ok()?;
            let iowait: u64 = parts[5].parse().ok()?;
            let irq: u64 = parts[6].parse().ok()?;
            let softirq: u64 = parts[7].parse().ok()?;
            
            let total = user + nice + system + idle + iowait + irq + softirq;
            let active = total - idle - iowait;
            
            if total > 0 {
                Some((active as f64 / total as f64) * 100.0)
            } else {
                None
            }
        } else {
            None
        }
    }
    
    /// Parse memory info from /proc/meminfo
    fn parse_memory_info(meminfo: &str) -> (u64, u64) {
        let mut total_kb = 0u64;
        let mut available_kb = 0u64;
        
        for line in meminfo.lines() {
            if line.starts_with("MemTotal:") {
                if let Some(value) = line.split_whitespace().nth(1) {
                    total_kb = value.parse().unwrap_or(0);
                }
            } else if line.starts_with("MemAvailable:") {
                if let Some(value) = line.split_whitespace().nth(1) {
                    available_kb = value.parse().unwrap_or(0);
                }
            }
        }
        
        (total_kb * 1024, available_kb * 1024) // Convert to bytes
    }
    
    /// Parse disk usage from /proc/diskstats
    fn parse_disk_usage(diskstats: &str) -> f64 {
        // Calculate actual disk I/O utilization based on read/write operations
        let mut total_io_time = 0u64;
        let mut device_count = 0u64;
        
        for line in diskstats.lines() {
            let fields: Vec<&str> = line.split_whitespace().collect();
            if fields.len() >= 13 {
                // Field 12 (index 12) contains total time spent doing I/Os (ms)
                if let Ok(io_time) = fields[12].parse::<u64>() {
                    total_io_time += io_time;
                    device_count += 1;
                }
            }
        }
        
        if device_count > 0 {
            // Calculate average I/O utilization as percentage
            // This is a simplified calculation - in production you'd track deltas over time
            let avg_io_time = total_io_time / device_count;
            // Convert to percentage (assuming max reasonable I/O time of 1000ms per sample)
            (avg_io_time as f64 / 1000.0).min(100.0)
        } else {
            0.0
        }
    }
    
    /// Parse network statistics from /proc/net/dev
    fn parse_network_stats(netdev: &str) -> (u64, u64) {
        let mut total_rx = 0u64;
        let mut total_tx = 0u64;
        
        for line in netdev.lines().skip(2) { // Skip header lines
            let parts: Vec<&str> = line.split_whitespace().collect();
            if parts.len() >= 10 {
                if let (Ok(rx), Ok(tx)) = (parts[1].parse::<u64>(), parts[9].parse::<u64>()) {
                    total_rx += rx;
                    total_tx += tx;
                }
            }
        }
        
        (total_rx, total_tx)
    }
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

/// Middleware to track request metrics
pub struct MetricsMiddleware;

impl<S, B> actix_web::dev::Transform<S, actix_web::dev::ServiceRequest> for MetricsMiddleware
where
    S: actix_web::dev::Service<
        actix_web::dev::ServiceRequest,
        Response = actix_web::dev::ServiceResponse<B>,
        Error = actix_web::Error,
    >,
    S::Future: 'static,
    B: 'static,
{
    type Response = actix_web::dev::ServiceResponse<B>;
    type Error = actix_web::Error;
    type Transform = MetricsMiddlewareService<S>;
    type InitError = ();
    type Future = std::future::Ready<Result<Self::Transform, Self::InitError>>;

    fn new_transform(&self, service: S) -> Self::Future {
        std::future::ready(Ok(MetricsMiddlewareService { service }))
    }
}

pub struct MetricsMiddlewareService<S> {
    service: S,
}

impl<S, B> actix_web::dev::Service<actix_web::dev::ServiceRequest> for MetricsMiddlewareService<S>
where
    S: actix_web::dev::Service<
        actix_web::dev::ServiceRequest,
        Response = actix_web::dev::ServiceResponse<B>,
        Error = actix_web::Error,
    >,
    S::Future: 'static,
    B: 'static,
{
    type Response = actix_web::dev::ServiceResponse<B>;
    type Error = actix_web::Error;
    type Future = Pin<Box<dyn std::future::Future<Output = Result<Self::Response, Self::Error>>>>;

    fn poll_ready(&self, cx: &mut std::task::Context<'_>) -> std::task::Poll<Result<(), Self::Error>> {
        self.service.poll_ready(cx)
    }

    fn call(&self, req: actix_web::dev::ServiceRequest) -> Self::Future {
        let start_time = std::time::Instant::now();
        let path = req.path().to_string();
        let method = req.method().to_string();
        
        let fut = self.service.call(req);
        
        Box::pin(async move {
            let res = fut.await?;
            let processing_time = start_time.elapsed().as_millis() as u64;
            let status_code = res.status().as_u16();
            let success = status_code < 400;
            
            // Try to get app state and record metrics
            if let Some(app_data) = res.request().app_data::<web::Data<AppState>>() {
                if let Ok(mut metrics) = app_data.metrics.try_write() {
                    let endpoint = format!("{} {}", method, path);
                    metrics.record_request(&endpoint, processing_time, success);
                    
                    if !success {
                        let error_type = format!("HTTP_{}", status_code);
                        metrics.record_error(&error_type);
                    }
                }
            }
            
            Ok(res)
        })
    }
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

    // Initialize Kafka messaging with retry logic
    let messaging = {
        let mut retry_count = 0;
        let max_retries = 10;
        loop {
            match KafkaMessaging::new(config.kafka.clone()) {
                Ok(messaging) => {
                    log::info!("Kafka messaging initialized successfully");
                    break Arc::new(messaging);
                }
                Err(e) => {
                    retry_count += 1;
                    if retry_count >= max_retries {
                        log::error!("Failed to initialize Kafka messaging after {} retries: {}", max_retries, e);
                        return Err(e);
                    }
                    log::warn!("Failed to connect to Kafka (attempt {}/{}): {}. Retrying in 5 seconds...", retry_count, max_retries, e);
                    tokio::time::sleep(tokio::time::Duration::from_secs(5)).await;
                }
            }
        }
    };

    // Initialize Pinecone storage
    let storage = Arc::new(PineconeClient::new(config.pinecone.clone())?);
    log::info!("Pinecone storage initialized");

    // Initialize template engine
    let mut tera = Tera::new("src/ui/templates/**/*")?;
    tera.autoescape_on(vec![".html"]);
    log::info!("Template engine initialized");

    // Create application state
    let app_state = web::Data::new(AppState {
        config: config.clone(),
        messaging: messaging.clone(),
        storage: storage.clone(),
        tera,
        pending_results: Arc::new(RwLock::new(HashMap::new())),
        metrics: Arc::new(RwLock::new(AppMetrics::default())),
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
            .wrap(MetricsMiddleware)
            .route("/", web::get().to(index_handler))
            .route("/submit", web::post().to(submit_handler))
            .route("/result/{request_id}", web::get().to(result_handler))
            .route("/feedback", web::post().to(feedback_handler))
            .route("/health", web::get().to(health_handler))
            .route("/userguide", web::get().to(userguide_handler))
            .route("/api/stats", web::get().to(stats_handler))
            .service(Files::new("/static", "src/ui/static").show_files_listing())
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
    while let Some(field) = payload.next().await {
        let mut field = field?;
        let content_disposition = field.content_disposition();
        
        if let Some(name) = content_disposition.get_name() {
            let name = name.to_string(); // Extract name to avoid borrowing issues
            if name.starts_with("file_") {
                // Handle file upload
                if let Some(filename) = content_disposition.get_filename() {
                    let filename = filename.to_string(); // Extract filename to avoid borrowing issues
                    let content_type = field.content_type()
                        .map(|ct| ct.to_string())
                        .unwrap_or_else(|| "application/octet-stream".to_string());
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
                    let document_type = match name.as_str() {
                        "file_id" => "id_document",
                        "file_selfie" => "selfie",
                        "file_passport" => "passport",
                        _ => "unknown",
                    };
                    
                    let document_info = DocumentInfo {
                        document_type: document_type.to_string(),
                        file_path,
                        filename: filename.clone(),
                        file_size: size as u64,
                        mime_type: content_type,
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
                    form_data.insert(name, value);
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
            "kafka": "healthy",
            "pinecone": "healthy"
        }
    });

    // Note: Kafka health is assumed healthy since the service started successfully
    // In a production environment, you would implement proper Kafka connectivity checks
    
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
    
    // Update and get current metrics
    let mut metrics = data.metrics.write().await;
    metrics.update_system_load();
    
    let uptime_seconds = metrics.uptime_seconds();
    let uptime_formatted = format_uptime(uptime_seconds);
    let avg_processing_time = metrics.average_processing_time();
    let success_rate = if metrics.total_requests > 0 {
        (metrics.successful_requests as f64 / metrics.total_requests as f64) * 100.0
    } else {
        0.0
    };
    
    let system_load = &metrics.system_load;
    let memory_usage_percent = if system_load.total_memory > 0 {
        (system_load.memory_usage as f64 / system_load.total_memory as f64) * 100.0
    } else {
        0.0
    };
    
    let stats = serde_json::json!({
        "pending_results": results_count,
        "uptime": uptime_formatted,
        "uptime_seconds": uptime_seconds,
        "processed_requests": metrics.total_requests,
        "successful_requests": metrics.successful_requests,
        "failed_requests": metrics.failed_requests,
        "success_rate_percent": format!("{:.2}", success_rate),
        "average_processing_time_ms": format!("{:.2}", avg_processing_time),
        "system_load": {
            "cpu_usage_percent": format!("{:.2}", system_load.cpu_usage),
            "memory_usage_bytes": system_load.memory_usage,
            "memory_total_bytes": system_load.total_memory,
            "memory_usage_percent": format!("{:.2}", memory_usage_percent),
            "disk_usage_percent": format!("{:.2}", system_load.disk_usage),
            "network_rx_bytes": system_load.network_rx_bytes,
            "network_tx_bytes": system_load.network_tx_bytes,
            "last_updated": system_load.last_updated.elapsed().as_secs()
        },
        "endpoint_counts": metrics.endpoint_counts,
        "error_counts": metrics.error_counts,
        "timestamp": chrono::Utc::now().to_rfc3339()
    });
    
    Ok(HttpResponse::Ok().json(stats))
}

/// Format uptime seconds into human-readable format
fn format_uptime(seconds: u64) -> String {
    let days = seconds / 86400;
    let hours = (seconds % 86400) / 3600;
    let minutes = (seconds % 3600) / 60;
    let secs = seconds % 60;
    
    if days > 0 {
        format!("{}d {}h {}m {}s", days, hours, minutes, secs)
    } else if hours > 0 {
        format!("{}h {}m {}s", hours, minutes, secs)
    } else if minutes > 0 {
        format!("{}m {}s", minutes, secs)
    } else {
        format!("{}s", secs)
    }
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
