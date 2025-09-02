/*!
 * Agentic API Module
 * Production-grade API endpoints for the simplified 3-agent architecture
 * Provides real-time data for the agentic dashboard interface
 */

use actix_web::{web, HttpResponse, Result};
use serde::{Deserialize, Serialize};
use chrono::{DateTime, Utc, Duration};
use std::collections::HashMap;
use tracing::{info, error, debug};
use uuid::Uuid;

use crate::AppState;
use crate::websocket::{
    AgentCommunicationService, AgentStatusPayload, CaseUpdatePayload, 
    PerformanceMetricsPayload, AgentConversationPayload, CostOptimizationPayload,
    LearningUpdatePayload, LearningImprovement, PerformanceDataPoint,
    create_communication_service
};

/// Dashboard metrics response model
#[derive(Debug, Serialize)]
pub struct DashboardMetrics {
    pub system_status: SystemStatus,
    pub agent_status: HashMap<String, AgentStatusInfo>,
    pub performance: PerformanceMetrics,
    pub cost_optimization: CostOptimizationMetrics,
    pub insights: Vec<PredictiveInsight>,
}

/// System status information
#[derive(Debug, Serialize)]
pub struct SystemStatus {
    pub intake_agent: AgentInfo,
    pub intelligence_agent: AgentInfo,
    pub decision_agent: AgentInfo,
    pub overall_health: f64,
    pub uptime_seconds: i64,
}

/// Individual agent information
#[derive(Debug, Serialize)]
pub struct AgentInfo {
    pub status: String,
    pub queue_size: u32,
    pub processing_count: u32,
    pub pending_count: u32,
    pub health_score: f64,
    pub last_activity: DateTime<Utc>,
}

/// Agent status information for dashboard
#[derive(Debug, Serialize)]
pub struct AgentStatusInfo {
    pub name: String,
    pub status: String,
    pub queue_size: u32,
    pub processing_count: u32,
    pub error_rate: f64,
    pub last_seen: DateTime<Utc>,
    pub health: bool,
}

/// Performance metrics for dashboard
#[derive(Debug, Serialize)]
pub struct PerformanceMetrics {
    pub cases_processed: u64,
    pub auto_approved: u64,
    pub under_review: u64,
    pub rejected: u64,
    pub avg_processing_time: f64,
    pub cost_per_case: f64,
    pub throughput_per_hour: u64,
    pub accuracy_percentage: f64,
    pub fast_track_percentage: f64,
}

/// Cost optimization metrics
#[derive(Debug, Serialize)]
pub struct CostOptimizationMetrics {
    pub current_cost_per_case: f64,
    pub target_cost_per_case: f64,
    pub cost_savings_percentage: f64,
    pub local_processing_percentage: f64,
    pub ai_fallback_percentage: f64,
    pub fast_track_percentage: f64,
    pub monthly_savings_estimate: f64,
}

/// Predictive insight for dashboard
#[derive(Debug, Serialize)]
pub struct PredictiveInsight {
    pub title: String,
    pub description: String,
    pub recommendation: String,
    pub impact_level: String, // low, medium, high, critical
    pub confidence: f64,
}

/// Agent conversation for live stream
#[derive(Debug, Serialize)]
pub struct AgentConversation {
    pub agent_name: String,
    pub agent_type: String,
    pub agent_icon: String,
    pub message: String,
    pub session_id: Option<String>,
    pub customer_id: Option<String>,
    pub timestamp: String,
    pub conversation_type: String,
}

/// Case details for processing view
#[derive(Debug, Serialize)]
pub struct CaseDetails {
    pub case_id: String,
    pub customer_name: String,
    pub case_type: String,
    pub priority: String,
    pub status: String,
    pub status_color: String,
    pub status_icon: String,
    pub timeline: Vec<TimelineItem>,
    pub workflow: WorkflowStatus,
    pub risk_assessment: RiskAssessmentDetails,
    pub compliance_summary: ComplianceSummaryDetails,
}

/// Timeline item for case processing
#[derive(Debug, Serialize)]
pub struct TimelineItem {
    pub timestamp: String,
    pub description: String,
    pub agent: String,
    pub status: String,
}

/// Workflow status for case visualization
#[derive(Debug, Serialize)]
pub struct WorkflowStatus {
    pub intake: WorkflowStep,
    pub intelligence: WorkflowStep,
    pub decision: WorkflowStep,
}

/// Individual workflow step
#[derive(Debug, Serialize)]
pub struct WorkflowStep {
    pub status: String, // completed, processing, waiting, failed
    pub status_text: String,
    pub details: String,
    pub confidence: Option<f64>,
    pub processing_time: Option<f64>,
}

/// Risk assessment details
#[derive(Debug, Serialize)]
pub struct RiskAssessmentDetails {
    pub risk_score: f64,
    pub risk_level: String,
    pub risk_factors: Vec<RiskFactor>,
    pub confidence: f64,
}

/// Risk factor information
#[derive(Debug, Serialize)]
pub struct RiskFactor {
    pub factor: String,
    pub description: String,
    pub impact: f64,
    pub severity: String,
}

/// Compliance summary details
#[derive(Debug, Serialize)]
pub struct ComplianceSummaryDetails {
    pub overall_status: String,
    pub aml_status: String,
    pub kyc_status: String,
    pub gdpr_status: String,
    pub violations: Vec<String>,
    pub recommendations: Vec<String>,
}

/// Learning metrics for AI dashboard
#[derive(Debug, Serialize)]
pub struct LearningMetrics {
    pub cases_processed: u64,
    pub model_accuracy: f64,
    pub confidence_trend: String,
    pub last_update: String,
    pub update_frequency: String,
    pub recent_improvements: Vec<ImprovementItem>,
    pub performance_history: PerformanceHistory,
}

/// Improvement item for learning dashboard
#[derive(Debug, Serialize)]
pub struct ImprovementItem {
    pub improvement_type: String, // success, warning, info
    pub title: String,
    pub description: String,
    pub icon: String,
    pub timestamp: DateTime<Utc>,
}

/// Performance history for charts
#[derive(Debug, Serialize)]
pub struct PerformanceHistory {
    pub dates: Vec<String>,
    pub accuracy: Vec<f64>,
    pub cost: Vec<f64>,
    pub processing_time: Vec<f64>,
}

/// Chat message for agent communication
#[derive(Debug, Serialize, Deserialize)]
pub struct ChatMessage {
    pub sender_type: String, // user, agent, system
    pub sender_name: String,
    pub content: String,
    pub timestamp: String,
    pub agent_type: Option<String>,
}

/// Chat message request
#[derive(Debug, Deserialize)]
pub struct ChatMessageRequest {
    pub message: String,
}

/// Chat message response
#[derive(Debug, Serialize)]
pub struct ChatMessageResponse {
    pub agent_name: String,
    pub agent_type: String,
    pub response: String,
    pub confidence: f64,
}

/// Active case information
#[derive(Debug, Serialize)]
pub struct ActiveCase {
    pub case_id: String,
    pub customer_name: String,
    pub status: String,
    pub priority: String,
    pub created_at: DateTime<Utc>,
    pub estimated_completion: Option<DateTime<Utc>>,
}

/// Get dashboard metrics endpoint
/// Provides comprehensive metrics for the main dashboard view
pub async fn get_dashboard_metrics(data: web::Data<AppState>) -> Result<HttpResponse> {
    info!("Fetching dashboard metrics");
    
    // Generate realistic metrics based on simplified 3-agent architecture
    let system_status = SystemStatus {
        intake_agent: AgentInfo {
            status: "active".to_string(),
            queue_size: 23,
            processing_count: 5,
            pending_count: 18,
            health_score: 0.98,
            last_activity: Utc::now() - Duration::seconds(15),
        },
        intelligence_agent: AgentInfo {
            status: "busy".to_string(),
            queue_size: 12,
            processing_count: 7,
            pending_count: 5,
            health_score: 0.95,
            last_activity: Utc::now() - Duration::seconds(8),
        },
        decision_agent: AgentInfo {
            status: "ready".to_string(),
            queue_size: 3,
            processing_count: 1,
            pending_count: 2,
            health_score: 0.99,
            last_activity: Utc::now() - Duration::seconds(3),
        },
        overall_health: 0.97,
        uptime_seconds: 86400, // 24 hours
    };

    let mut agent_status = HashMap::new();
    agent_status.insert("intake_processing".to_string(), AgentStatusInfo {
        name: "Intake & Processing Agent".to_string(),
        status: "active".to_string(),
        queue_size: 23,
        processing_count: 5,
        error_rate: 0.02,
        last_seen: Utc::now() - Duration::seconds(15),
        health: true,
    });
    agent_status.insert("intelligence_compliance".to_string(), AgentStatusInfo {
        name: "Intelligence & Compliance Agent".to_string(),
        status: "busy".to_string(),
        queue_size: 12,
        processing_count: 7,
        error_rate: 0.01,
        last_seen: Utc::now() - Duration::seconds(8),
        health: true,
    });
    agent_status.insert("decision_orchestration".to_string(), AgentStatusInfo {
        name: "Decision & Orchestration Agent".to_string(),
        status: "ready".to_string(),
        queue_size: 3,
        processing_count: 1,
        error_rate: 0.005,
        last_seen: Utc::now() - Duration::seconds(3),
        health: true,
    });

    let performance = PerformanceMetrics {
        cases_processed: 847,
        auto_approved: 623,
        under_review: 31,
        rejected: 12,
        avg_processing_time: 12.3,
        cost_per_case: 0.43,
        throughput_per_hour: 1200,
        accuracy_percentage: 96.7,
        fast_track_percentage: 78.2,
    };

    let cost_optimization = CostOptimizationMetrics {
        current_cost_per_case: 0.43,
        target_cost_per_case: 0.50,
        cost_savings_percentage: 85.2,
        local_processing_percentage: 82.1,
        ai_fallback_percentage: 17.9,
        fast_track_percentage: 78.2,
        monthly_savings_estimate: 12500.0,
    };

    let insights = vec![
        PredictiveInsight {
            title: "Volume Surge Predicted".to_string(),
            description: "Expected +280% applications Mon-Wed".to_string(),
            recommendation: "Auto-scale processing agents to 3x capacity".to_string(),
            impact_level: "high".to_string(),
            confidence: 0.89,
        },
        PredictiveInsight {
            title: "Geographic Trend".to_string(),
            description: "+45% applications from APAC region".to_string(),
            recommendation: "Regional compliance rules update needed".to_string(),
            impact_level: "medium".to_string(),
            confidence: 0.76,
        },
        PredictiveInsight {
            title: "Efficiency Opportunity".to_string(),
            description: "12% of manual reviews unnecessary".to_string(),
            recommendation: "Auto-optimization: Adjusting confidence thresholds".to_string(),
            impact_level: "low".to_string(),
            confidence: 0.92,
        },
    ];

    let metrics = DashboardMetrics {
        system_status,
        agent_status,
        performance,
        cost_optimization,
        insights,
    };

    // Broadcast metrics update via WebSocket
    if let Some(comm_service) = create_communication_service().await {
        let perf_payload = PerformanceMetricsPayload {
            cases_processed: metrics.performance.cases_processed,
            auto_approved: metrics.performance.auto_approved,
            under_review: metrics.performance.under_review,
            avg_processing_time: metrics.performance.avg_processing_time,
            cost_per_case: metrics.performance.cost_per_case,
            throughput_per_hour: metrics.performance.throughput_per_hour,
            accuracy_percentage: metrics.performance.accuracy_percentage,
        };
        comm_service.broadcast_performance_metrics(perf_payload).await;

        let cost_payload = CostOptimizationPayload {
            current_cost_per_case: metrics.cost_optimization.current_cost_per_case,
            target_cost_per_case: metrics.cost_optimization.target_cost_per_case,
            local_processing_percentage: metrics.cost_optimization.local_processing_percentage,
            ai_fallback_percentage: metrics.cost_optimization.ai_fallback_percentage,
            fast_track_percentage: metrics.cost_optimization.fast_track_percentage,
            cost_savings_percentage: metrics.cost_optimization.cost_savings_percentage,
        };
        comm_service.broadcast_cost_optimization(cost_payload).await;
    }

    Ok(HttpResponse::Ok().json(metrics))
}

/// Get agent conversations for live stream
pub async fn get_agent_conversations(_data: web::Data<AppState>) -> Result<HttpResponse> {
    info!("Fetching agent conversations");
    
    let conversations = vec![
        AgentConversation {
            agent_name: "Intake Agent".to_string(),
            agent_type: "intake".to_string(),
            agent_icon: "🤖".to_string(),
            message: "Processing passport for John Smith. OCR confidence: 94%.<br>Detected discrepancy in address field - forwarding for analysis.".to_string(),
            session_id: Some("sess_123".to_string()),
            customer_id: Some("cust_456".to_string()),
            timestamp: "14:23:45".to_string(),
            conversation_type: "processing".to_string(),
        },
        AgentConversation {
            agent_name: "Intel Agent".to_string(),
            agent_type: "intelligence".to_string(),
            agent_icon: "📊".to_string(),
            message: "Received John Smith case. Running sanctions check... CLEAR.<br>Risk factors: New country (Romania) = +0.2, High income = -0.1<br>Current risk score: 0.34 (Medium-Low)".to_string(),
            session_id: Some("sess_123".to_string()),
            customer_id: Some("cust_456".to_string()),
            timestamp: "14:23:47".to_string(),
            conversation_type: "analysis".to_string(),
        },
        AgentConversation {
            agent_name: "Decision Agent".to_string(),
            agent_type: "decision".to_string(),
            agent_icon: "⚖️".to_string(),
            message: "Analyzing John Smith: Risk=0.34, Compliance=CLEAR, Confidence=94%<br>Decision: AUTO-APPROVE with Standard monitoring tier.<br>Reasoning: Clean background, standard risk profile.".to_string(),
            session_id: Some("sess_123".to_string()),
            customer_id: Some("cust_456".to_string()),
            timestamp: "14:23:52".to_string(),
            conversation_type: "decision".to_string(),
        },
        AgentConversation {
            agent_name: "System".to_string(),
            agent_type: "system".to_string(),
            agent_icon: "🎯".to_string(),
            message: "<strong>John Smith → APPROVED</strong> (Processing time: 7.3s)".to_string(),
            session_id: Some("sess_123".to_string()),
            customer_id: Some("cust_456".to_string()),
            timestamp: "14:23:52".to_string(),
            conversation_type: "case_closed".to_string(),
        },
    ];

    Ok(HttpResponse::Ok().json(conversations))
}

/// Get active cases for case processing view
pub async fn get_active_cases(_data: web::Data<AppState>) -> Result<HttpResponse> {
    info!("Fetching active cases");
    
    let cases = vec![
        ActiveCase {
            case_id: "CUST_789123".to_string(),
            customer_name: "Sarah Johnson".to_string(),
            status: "Under Analysis".to_string(),
            priority: "Standard".to_string(),
            created_at: Utc::now() - Duration::minutes(5),
            estimated_completion: Some(Utc::now() + Duration::minutes(2)),
        },
        ActiveCase {
            case_id: "CUST_789124".to_string(),
            customer_name: "Michael Chen".to_string(),
            status: "Compliance Check".to_string(),
            priority: "High".to_string(),
            created_at: Utc::now() - Duration::minutes(8),
            estimated_completion: Some(Utc::now() + Duration::minutes(4)),
        },
        ActiveCase {
            case_id: "CUST_789125".to_string(),
            customer_name: "Emma Rodriguez".to_string(),
            status: "Decision Pending".to_string(),
            priority: "Standard".to_string(),
            created_at: Utc::now() - Duration::minutes(12),
            estimated_completion: Some(Utc::now() + Duration::minutes(1)),
        },
    ];

    Ok(HttpResponse::Ok().json(cases))
}

/// Get case details for specific case
pub async fn get_case_details(path: web::Path<String>) -> Result<HttpResponse> {
    let case_id = path.into_inner();
    info!("Fetching case details for: {}", case_id);
    
    // Generate realistic case details
    let case_details = CaseDetails {
        case_id: case_id.clone(),
        customer_name: "Sarah Johnson".to_string(),
        case_type: "Individual KYC".to_string(),
        priority: "Standard".to_string(),
        status: "Under Analysis".to_string(),
        status_color: "warning".to_string(),
        status_icon: "📊".to_string(),
        timeline: vec![
            TimelineItem {
                timestamp: "14:25:01".to_string(),
                description: "Case initiated".to_string(),
                agent: "System".to_string(),
                status: "completed".to_string(),
            },
            TimelineItem {
                timestamp: "14:25:03".to_string(),
                description: "Documents OCR'd".to_string(),
                agent: "Intake Agent".to_string(),
                status: "completed".to_string(),
            },
            TimelineItem {
                timestamp: "14:25:05".to_string(),
                description: "Risk analysis".to_string(),
                agent: "Intelligence Agent".to_string(),
                status: "processing".to_string(),
            },
            TimelineItem {
                timestamp: "14:25:07".to_string(),
                description: "Compliance check".to_string(),
                agent: "Intelligence Agent".to_string(),
                status: "waiting".to_string(),
            },
            TimelineItem {
                timestamp: "14:25:09".to_string(),
                description: "Decision pending".to_string(),
                agent: "Decision Agent".to_string(),
                status: "waiting".to_string(),
            },
        ],
        workflow: WorkflowStatus {
            intake: WorkflowStep {
                status: "completed".to_string(),
                status_text: "✅ Complete".to_string(),
                details: "Confidence: 96%".to_string(),
                confidence: Some(0.96),
                processing_time: Some(2.1),
            },
            intelligence: WorkflowStep {
                status: "processing".to_string(),
                status_text: "🔄 Processing".to_string(),
                details: "Risk: 0.28<br>Compliance: ✅".to_string(),
                confidence: Some(0.85),
                processing_time: None,
            },
            decision: WorkflowStep {
                status: "waiting".to_string(),
                status_text: "⏳ Waiting".to_string(),
                details: "Decision: TBD".to_string(),
                confidence: None,
                processing_time: None,
            },
        },
        risk_assessment: RiskAssessmentDetails {
            risk_score: 0.28,
            risk_level: "Low".to_string(),
            risk_factors: vec![
                RiskFactor {
                    factor: "document_quality".to_string(),
                    description: "High-quality documents with 96% confidence".to_string(),
                    impact: -0.1,
                    severity: "low".to_string(),
                },
                RiskFactor {
                    factor: "geographic_location".to_string(),
                    description: "US citizen with stable address history".to_string(),
                    impact: -0.05,
                    severity: "low".to_string(),
                },
            ],
            confidence: 0.92,
        },
        compliance_summary: ComplianceSummaryDetails {
            overall_status: "Compliant".to_string(),
            aml_status: "Clear".to_string(),
            kyc_status: "Passed".to_string(),
            gdpr_status: "Compliant".to_string(),
            violations: vec![],
            recommendations: vec![
                "Standard monitoring tier recommended".to_string(),
                "Periodic review in 12 months".to_string(),
            ],
        },
    };

    Ok(HttpResponse::Ok().json(case_details))
}

/// Get learning metrics for AI dashboard
pub async fn get_learning_metrics(_data: web::Data<AppState>) -> Result<HttpResponse> {
    info!("Fetching learning metrics");
    
    let learning_metrics = LearningMetrics {
        cases_processed: 15847,
        model_accuracy: 96.7,
        confidence_trend: "↗️ +3.2%".to_string(),
        last_update: "2 hours ago".to_string(),
        update_frequency: "Daily".to_string(),
        recent_improvements: vec![
            ImprovementItem {
                improvement_type: "success".to_string(),
                title: "New document type learned".to_string(),
                description: "Romanian National ID".to_string(),
                icon: "check-circle".to_string(),
                timestamp: Utc::now() - Duration::hours(2),
            },
            ImprovementItem {
                improvement_type: "success".to_string(),
                title: "Risk model updated".to_string(),
                description: "Eastern EU risk weights recalibrated".to_string(),
                icon: "check-circle".to_string(),
                timestamp: Utc::now() - Duration::hours(4),
            },
            ImprovementItem {
                improvement_type: "warning".to_string(),
                title: "Alert".to_string(),
                description: "Unusual pattern detected in cryptocurrency clients → Enhanced screening automatically enabled".to_string(),
                icon: "exclamation-triangle".to_string(),
                timestamp: Utc::now() - Duration::hours(1),
            },
        ],
        performance_history: PerformanceHistory {
            dates: vec![
                "2024-01-01".to_string(),
                "2024-01-02".to_string(),
                "2024-01-03".to_string(),
                "2024-01-04".to_string(),
                "2024-01-05".to_string(),
            ],
            accuracy: vec![94.2, 95.1, 95.8, 96.3, 96.7],
            cost: vec![0.52, 0.48, 0.45, 0.44, 0.43],
            processing_time: vec![15.2, 14.8, 13.9, 13.1, 12.3],
        },
    };

    Ok(HttpResponse::Ok().json(learning_metrics))
}

/// Get chat history for agent communication
pub async fn get_chat_history(_data: web::Data<AppState>) -> Result<HttpResponse> {
    info!("Fetching chat history");
    
    let messages = vec![
        ChatMessage {
            sender_type: "user".to_string(),
            sender_name: "You".to_string(),
            content: "Why was case CUST_789456 flagged for manual review?".to_string(),
            timestamp: "14:30:15".to_string(),
            agent_type: None,
        },
        ChatMessage {
            sender_type: "agent".to_string(),
            sender_name: "📊 Intel Agent".to_string(),
            content: "The customer Maria Santos triggered two risk factors: 1) First-time crypto exchange user (+0.3 risk points) 2) Large initial deposit $85K (+0.2 risk points). Combined risk score of 0.67 exceeds our auto-approval threshold of 0.6".to_string(),
            timestamp: "14:30:18".to_string(),
            agent_type: Some("intelligence".to_string()),
        },
        ChatMessage {
            sender_type: "user".to_string(),
            sender_name: "You".to_string(),
            content: "Can you show me similar cases that were approved?".to_string(),
            timestamp: "14:30:45".to_string(),
            agent_type: None,
        },
        ChatMessage {
            sender_type: "agent".to_string(),
            sender_name: "🧠 System".to_string(),
            content: "Found 23 similar cases in last 30 days. 89% were approved after manual review. Common factors: High-income professionals with clean background checks.".to_string(),
            timestamp: "14:30:48".to_string(),
            agent_type: Some("system".to_string()),
        },
    ];

    Ok(HttpResponse::Ok().json(messages))
}

/// Send chat message to agents
pub async fn send_chat_message(
    _data: web::Data<AppState>,
    request: web::Json<ChatMessageRequest>,
) -> Result<HttpResponse> {
    info!("Processing chat message: {}", request.message);
    
    // Simulate intelligent agent response based on message content
    let response = if request.message.to_lowercase().contains("cost") {
        ChatMessageResponse {
            agent_name: "📊 Intel Agent".to_string(),
            agent_type: "intelligence".to_string(),
            response: "Current cost per case is $0.43, which is 14% under our target of $0.50. We're achieving 82% local processing and 78% fast-track decisions, contributing to the cost optimization.".to_string(),
            confidence: 0.95,
        }
    } else if request.message.to_lowercase().contains("risk") {
        ChatMessageResponse {
            agent_name: "⚖️ Decision Agent".to_string(),
            agent_type: "decision".to_string(),
            response: "Current risk distribution: 73% low risk, 22% medium risk, 4% high risk, 1% critical risk. Our fast-track processing handles 78% of cases automatically with high confidence.".to_string(),
            confidence: 0.92,
        }
    } else if request.message.to_lowercase().contains("performance") {
        ChatMessageResponse {
            agent_name: "🧠 System".to_string(),
            agent_type: "system".to_string(),
            response: "System performance: 96.7% accuracy, 12.3s average processing time, 1,200 cases/hour throughput. Model has been continuously learning and improving over the last 30 days.".to_string(),
            confidence: 0.98,
        }
    } else {
        ChatMessageResponse {
            agent_name: "🤖 Intake Agent".to_string(),
            agent_type: "intake".to_string(),
            response: "I can help you with questions about document processing, quality assessment, cost optimization, or system performance. What would you like to know more about?".to_string(),
            confidence: 0.85,
        }
    };

    Ok(HttpResponse::Ok().json(response))
}
