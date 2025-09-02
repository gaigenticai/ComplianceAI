/*!
 * WebSocket Module for Real-time Agent Communication
 * Production-grade WebSocket implementation for live agent status updates,
 * conversation streams, and interactive case processing visualization
 */

use actix::{Actor, StreamHandler, Handler, Message, ActorContext, Addr, AsyncContext};
use actix_web::{web, HttpRequest, HttpResponse, Error, Result};
use actix_web_actors::ws;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::sync::Arc;
use tokio::sync::RwLock;
use uuid::Uuid;
use chrono::{DateTime, Utc};
use tracing::{info, warn, error, debug};
use dashmap::DashMap;

use crate::AppState;

/// WebSocket message types for agent communication
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(tag = "type")]
pub enum AgentMessage {
    /// Agent status update message
    AgentStatusUpdate {
        payload: AgentStatusPayload,
    },
    /// Case processing update message
    CaseUpdate {
        payload: CaseUpdatePayload,
    },
    /// Performance metrics update message
    PerformanceMetrics {
        payload: PerformanceMetricsPayload,
    },
    /// Agent conversation message for live stream
    AgentConversation {
        payload: AgentConversationPayload,
    },
    /// Cost optimization metrics update
    CostOptimization {
        payload: CostOptimizationPayload,
    },
    /// Learning and model performance update
    LearningUpdate {
        payload: LearningUpdatePayload,
    },
    /// Client subscription message
    Subscribe {
        topics: Vec<String>,
    },
    /// Client unsubscription message
    Unsubscribe {
        topics: Vec<String>,
    },
    /// Heartbeat message for connection health
    Heartbeat,
    /// Error message
    Error {
        message: String,
        code: Option<String>,
    },
}

/// Agent status payload for real-time updates
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AgentStatusPayload {
    pub agent_name: String,
    pub status: String, // active, busy, ready, error
    pub queue_size: u32,
    pub processing_count: u32,
    pub last_activity: DateTime<Utc>,
    pub health_score: f64,
    pub error_rate: f64,
}

/// Case processing update payload
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CaseUpdatePayload {
    pub session_id: String,
    pub customer_id: String,
    pub current_stage: String,
    pub progress_percentage: u8,
    pub agent_workflow: HashMap<String, WorkflowStepStatus>,
    pub estimated_completion: Option<DateTime<Utc>>,
}

/// Workflow step status for case visualization
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct WorkflowStepStatus {
    pub status: String, // completed, processing, waiting, failed
    pub confidence: Option<f64>,
    pub processing_time: Option<f64>,
    pub details: Option<String>,
}

/// Performance metrics payload
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PerformanceMetricsPayload {
    pub cases_processed: u64,
    pub auto_approved: u64,
    pub under_review: u64,
    pub avg_processing_time: f64,
    pub cost_per_case: f64,
    pub throughput_per_hour: u64,
    pub accuracy_percentage: f64,
}

/// Agent conversation payload for live stream
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AgentConversationPayload {
    pub agent_name: String,
    pub agent_type: String, // intake, intelligence, decision
    pub agent_icon: String,
    pub message: String,
    pub session_id: Option<String>,
    pub customer_id: Option<String>,
    pub timestamp: DateTime<Utc>,
    pub conversation_type: String, // processing, decision, error, system
}

/// Cost optimization metrics payload
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CostOptimizationPayload {
    pub current_cost_per_case: f64,
    pub target_cost_per_case: f64,
    pub local_processing_percentage: f64,
    pub ai_fallback_percentage: f64,
    pub fast_track_percentage: f64,
    pub cost_savings_percentage: f64,
}

/// Learning and model performance update payload
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LearningUpdatePayload {
    pub cases_processed: u64,
    pub model_accuracy: f64,
    pub confidence_trend: f64,
    pub last_model_update: DateTime<Utc>,
    pub recent_improvements: Vec<LearningImprovement>,
    pub performance_history: Vec<PerformanceDataPoint>,
}

/// Learning improvement item
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LearningImprovement {
    pub improvement_type: String, // success, warning, info
    pub title: String,
    pub description: String,
    pub impact_score: f64,
    pub timestamp: DateTime<Utc>,
}

/// Performance data point for charts
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PerformanceDataPoint {
    pub timestamp: DateTime<Utc>,
    pub accuracy: f64,
    pub cost: f64,
    pub processing_time: f64,
}

/// WebSocket connection actor
pub struct AgentWebSocket {
    /// Unique connection ID
    pub connection_id: String,
    /// Subscribed topics for filtering messages
    pub subscriptions: Vec<String>,
    /// Reference to application state
    pub app_state: web::Data<AppState>,
    /// Connection manager address
    pub connection_manager: Addr<ConnectionManager>,
}

impl AgentWebSocket {
    /// Create new WebSocket connection
    pub fn new(app_state: web::Data<AppState>, connection_manager: Addr<ConnectionManager>) -> Self {
        Self {
            connection_id: Uuid::new_v4().to_string(),
            subscriptions: Vec::new(),
            app_state,
            connection_manager,
        }
    }

    /// Handle subscription to topics
    fn handle_subscribe(&mut self, topics: Vec<String>) {
        debug!("Connection {} subscribing to topics: {:?}", self.connection_id, topics);
        
        for topic in topics {
            if !self.subscriptions.contains(&topic) {
                self.subscriptions.push(topic);
            }
        }
        
        info!("Connection {} now subscribed to {} topics", self.connection_id, self.subscriptions.len());
    }

    /// Handle unsubscription from topics
    fn handle_unsubscribe(&mut self, topics: Vec<String>) {
        debug!("Connection {} unsubscribing from topics: {:?}", self.connection_id, topics);
        
        for topic in topics {
            self.subscriptions.retain(|t| t != &topic);
        }
        
        info!("Connection {} now subscribed to {} topics", self.connection_id, self.subscriptions.len());
    }

    /// Send message to client
    fn send_message(&self, ctx: &mut ws::WebsocketContext<Self>, message: &AgentMessage) {
        match serde_json::to_string(message) {
            Ok(json) => {
                ctx.text(json);
                debug!("Sent message to connection {}: {:?}", self.connection_id, message);
            }
            Err(e) => {
                error!("Failed to serialize message for connection {}: {}", self.connection_id, e);
                let error_msg = AgentMessage::Error {
                    message: "Failed to serialize message".to_string(),
                    code: Some("SERIALIZATION_ERROR".to_string()),
                };
                if let Ok(error_json) = serde_json::to_string(&error_msg) {
                    ctx.text(error_json);
                }
            }
        }
    }
}

impl Actor for AgentWebSocket {
    type Context = ws::WebsocketContext<Self>;

    /// Called when WebSocket connection starts
    fn started(&mut self, ctx: &mut Self::Context) {
        info!("WebSocket connection started: {}", self.connection_id);
        
        // Register connection with manager
        self.connection_manager.do_send(RegisterConnection {
            connection_id: self.connection_id.clone(),
            addr: ctx.address(),
        });

        // Send initial heartbeat
        ctx.run_interval(std::time::Duration::from_secs(30), |act, ctx| {
            let heartbeat = AgentMessage::Heartbeat;
            act.send_message(ctx, &heartbeat);
        });

        // Subscribe to default topics
        self.handle_subscribe(vec![
            "agent_status".to_string(),
            "performance_metrics".to_string(),
            "cost_optimization".to_string(),
        ]);
    }

    /// Called when WebSocket connection stops
    fn stopped(&mut self, _ctx: &mut Self::Context) {
        info!("WebSocket connection stopped: {}", self.connection_id);
        
        // Unregister connection from manager
        self.connection_manager.do_send(UnregisterConnection {
            connection_id: self.connection_id.clone(),
        });
    }
}

/// Handle WebSocket text messages from clients
impl StreamHandler<Result<ws::Message, ws::ProtocolError>> for AgentWebSocket {
    fn handle(&mut self, msg: Result<ws::Message, ws::ProtocolError>, ctx: &mut Self::Context) {
        match msg {
            Ok(ws::Message::Ping(msg)) => {
                debug!("Received ping from connection {}", self.connection_id);
                ctx.pong(&msg);
            }
            Ok(ws::Message::Pong(_)) => {
                debug!("Received pong from connection {}", self.connection_id);
            }
            Ok(ws::Message::Text(text)) => {
                debug!("Received text message from connection {}: {}", self.connection_id, text);
                
                match serde_json::from_str::<AgentMessage>(&text) {
                    Ok(agent_msg) => {
                        match agent_msg {
                            AgentMessage::Subscribe { topics } => {
                                self.handle_subscribe(topics);
                            }
                            AgentMessage::Unsubscribe { topics } => {
                                self.handle_unsubscribe(topics);
                            }
                            AgentMessage::Heartbeat => {
                                // Respond with heartbeat
                                let response = AgentMessage::Heartbeat;
                                self.send_message(ctx, &response);
                            }
                            _ => {
                                warn!("Received unexpected message type from connection {}", self.connection_id);
                            }
                        }
                    }
                    Err(e) => {
                        error!("Failed to parse message from connection {}: {}", self.connection_id, e);
                        let error_msg = AgentMessage::Error {
                            message: format!("Invalid message format: {}", e),
                            code: Some("PARSE_ERROR".to_string()),
                        };
                        self.send_message(ctx, &error_msg);
                    }
                }
            }
            Ok(ws::Message::Binary(_)) => {
                warn!("Received binary message from connection {} (not supported)", self.connection_id);
            }
            Ok(ws::Message::Close(reason)) => {
                info!("Connection {} closed: {:?}", self.connection_id, reason);
                ctx.stop();
            }
            Ok(ws::Message::Continuation(_)) => {
                // Handle continuation frames (usually not needed for simple text messages)
                debug!("Received continuation frame from connection {}", self.connection_id);
            }
            Ok(ws::Message::Nop) => {
                // Handle no-op frames
                debug!("Received nop frame from connection {}", self.connection_id);
            }
            Err(e) => {
                error!("WebSocket error for connection {}: {}", self.connection_id, e);
                ctx.stop();
            }
        }
    }
}

/// Message to broadcast to all connections
#[derive(Message)]
#[rtype(result = "()")]
pub struct BroadcastMessage {
    pub message: AgentMessage,
    pub topic: String,
}

/// Message to register a new connection
#[derive(Message)]
#[rtype(result = "()")]
pub struct RegisterConnection {
    pub connection_id: String,
    pub addr: Addr<AgentWebSocket>,
}

/// Message to unregister a connection
#[derive(Message)]
#[rtype(result = "()")]
pub struct UnregisterConnection {
    pub connection_id: String,
}

/// Connection manager actor for handling WebSocket connections
pub struct ConnectionManager {
    /// Active WebSocket connections
    connections: HashMap<String, Addr<AgentWebSocket>>,
    /// Topic subscriptions mapping
    topic_subscriptions: HashMap<String, Vec<String>>,
}

impl ConnectionManager {
    /// Create new connection manager
    pub fn new() -> Self {
        Self {
            connections: HashMap::new(),
            topic_subscriptions: HashMap::new(),
        }
    }

    /// Broadcast message to subscribed connections
    fn broadcast_to_topic(&self, topic: &str, message: &AgentMessage) {
        if let Some(connection_ids) = self.topic_subscriptions.get(topic) {
            for connection_id in connection_ids {
                if let Some(addr) = self.connections.get(connection_id) {
                    addr.do_send(BroadcastToConnection {
                        message: message.clone(),
                    });
                }
            }
        }
    }
}

impl Actor for ConnectionManager {
    type Context = actix::Context<Self>;

    fn started(&mut self, _ctx: &mut Self::Context) {
        info!("Connection manager started");
    }
}

/// Handle connection registration
impl Handler<RegisterConnection> for ConnectionManager {
    type Result = ();

    fn handle(&mut self, msg: RegisterConnection, _ctx: &mut Self::Context) {
        info!("Registering WebSocket connection: {}", msg.connection_id);
        self.connections.insert(msg.connection_id, msg.addr);
    }
}

/// Handle connection unregistration
impl Handler<UnregisterConnection> for ConnectionManager {
    type Result = ();

    fn handle(&mut self, msg: UnregisterConnection, _ctx: &mut Self::Context) {
        info!("Unregistering WebSocket connection: {}", msg.connection_id);
        self.connections.remove(&msg.connection_id);
        
        // Remove from topic subscriptions
        for (_, subscribers) in self.topic_subscriptions.iter_mut() {
            subscribers.retain(|id| id != &msg.connection_id);
        }
    }
}

/// Handle broadcast messages
impl Handler<BroadcastMessage> for ConnectionManager {
    type Result = ();

    fn handle(&mut self, msg: BroadcastMessage, _ctx: &mut Self::Context) {
        debug!("Broadcasting message to topic: {}", msg.topic);
        self.broadcast_to_topic(&msg.topic, &msg.message);
    }
}

/// Message to send to specific connection
#[derive(Message)]
#[rtype(result = "()")]
pub struct BroadcastToConnection {
    pub message: AgentMessage,
}

/// Handle broadcast to specific connection
impl Handler<BroadcastToConnection> for AgentWebSocket {
    type Result = ();

    fn handle(&mut self, msg: BroadcastToConnection, ctx: &mut Self::Context) {
        self.send_message(ctx, &msg.message);
    }
}

/// WebSocket endpoint handler
pub async fn websocket_handler(
    req: HttpRequest,
    stream: web::Payload,
    app_state: web::Data<AppState>,
    connection_manager: web::Data<Addr<ConnectionManager>>,
) -> Result<HttpResponse, Error> {
    info!("New WebSocket connection request from: {:?}", req.peer_addr());
    
    let ws_actor = AgentWebSocket::new(app_state, connection_manager.get_ref().clone());
    
    ws::start(ws_actor, &req, stream)
}

/// Agent communication service for broadcasting updates
pub struct AgentCommunicationService {
    connection_manager: Addr<ConnectionManager>,
}

impl AgentCommunicationService {
    /// Create new agent communication service
    pub fn new(connection_manager: Addr<ConnectionManager>) -> Self {
        Self {
            connection_manager,
        }
    }

    /// Broadcast agent status update
    pub async fn broadcast_agent_status(&self, payload: AgentStatusPayload) {
        let message = AgentMessage::AgentStatusUpdate { payload };
        self.connection_manager.do_send(BroadcastMessage {
            message,
            topic: "agent_status".to_string(),
        });
    }

    /// Broadcast case update
    pub async fn broadcast_case_update(&self, payload: CaseUpdatePayload) {
        let message = AgentMessage::CaseUpdate { payload };
        self.connection_manager.do_send(BroadcastMessage {
            message,
            topic: "case_updates".to_string(),
        });
    }

    /// Broadcast performance metrics
    pub async fn broadcast_performance_metrics(&self, payload: PerformanceMetricsPayload) {
        let message = AgentMessage::PerformanceMetrics { payload };
        self.connection_manager.do_send(BroadcastMessage {
            message,
            topic: "performance_metrics".to_string(),
        });
    }

    /// Broadcast agent conversation
    pub async fn broadcast_agent_conversation(&self, payload: AgentConversationPayload) {
        let message = AgentMessage::AgentConversation { payload };
        self.connection_manager.do_send(BroadcastMessage {
            message,
            topic: "agent_conversations".to_string(),
        });
    }

    /// Broadcast cost optimization metrics
    pub async fn broadcast_cost_optimization(&self, payload: CostOptimizationPayload) {
        let message = AgentMessage::CostOptimization { payload };
        self.connection_manager.do_send(BroadcastMessage {
            message,
            topic: "cost_optimization".to_string(),
        });
    }

    /// Broadcast learning update
    pub async fn broadcast_learning_update(&self, payload: LearningUpdatePayload) {
        let message = AgentMessage::LearningUpdate { payload };
        self.connection_manager.do_send(BroadcastMessage {
            message,
            topic: "learning_updates".to_string(),
        });
    }
}

/// Global connection manager instance
static CONNECTION_MANAGER: once_cell::sync::Lazy<Arc<RwLock<Option<Addr<ConnectionManager>>>>> =
    once_cell::sync::Lazy::new(|| Arc::new(RwLock::new(None)));

/// Initialize the global connection manager (simplified for startup)
pub async fn initialize_connection_manager() -> Addr<ConnectionManager> {
    // For now, return a dummy address to avoid startup issues
    // The actual connection manager will be initialized when the first WebSocket connects
    use actix::prelude::*;
    
    // Create a simple actor system context
    let system = System::new();
    let manager = system.block_on(async {
        ConnectionManager::new().start()
    });
    
    {
        let mut global_manager = CONNECTION_MANAGER.write().await;
        *global_manager = Some(manager.clone());
    }
    
    info!("Global connection manager initialized");
    manager
}

/// Get the global connection manager
pub async fn get_connection_manager() -> Option<Addr<ConnectionManager>> {
    let global_manager = CONNECTION_MANAGER.read().await;
    global_manager.clone()
}

/// Create agent communication service instance
pub async fn create_communication_service() -> Option<AgentCommunicationService> {
    if let Some(manager) = get_connection_manager().await {
        Some(AgentCommunicationService::new(manager))
    } else {
        error!("Connection manager not initialized");
        None
    }
}
