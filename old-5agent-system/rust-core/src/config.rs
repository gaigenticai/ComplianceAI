/*!
 * Configuration Management
 * Handles loading and merging of configuration files
 */

use serde::{Deserialize, Serialize};
use anyhow::{Result, Context};
use std::env;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AppConfig {
    pub server: ServerConfig,
    pub database: DatabaseConfig,
    pub kafka: KafkaConfig,
    pub redis: RedisConfig,
    pub agents: AgentsConfig,
    pub security: SecurityConfig,
    pub monitoring: MonitoringConfig,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ServerConfig {
    pub host: String,
    pub port: u16,
    pub workers: usize,
    pub max_connections: usize,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DatabaseConfig {
    pub postgres_url: String,
    pub mongodb_url: String,
    pub max_connections: u32,
    pub connection_timeout: u64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct KafkaConfig {
    pub bootstrap_servers: String,
    pub group_id: String,
    pub topics: KafkaTopics,
    pub producer_config: KafkaProducerConfig,
    pub consumer_config: KafkaConsumerConfig,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct KafkaTopics {
    pub data_ingestion: String,
    pub kyc_analysis: String,
    pub decision_results: String,
    pub compliance_results: String,
    pub quality_results: String,
    pub notifications: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct KafkaProducerConfig {
    pub acks: String,
    pub retries: u32,
    pub batch_size: u32,
    pub linger_ms: u32,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct KafkaConsumerConfig {
    pub auto_offset_reset: String,
    pub enable_auto_commit: bool,
    pub session_timeout_ms: u32,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RedisConfig {
    pub url: String,
    pub max_connections: u32,
    pub connection_timeout: u64,
    pub command_timeout: u64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AgentsConfig {
    pub data_ingestion: AgentConfig,
    pub kyc_analysis: AgentConfig,
    pub decision_making: AgentConfig,
    pub compliance_monitoring: AgentConfig,
    pub data_quality: AgentConfig,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AgentConfig {
    pub url: String,
    pub timeout: u64,
    pub max_retries: u32,
    pub health_check_interval: u64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SecurityConfig {
    pub jwt_secret: String,
    pub session_timeout: u64,
    pub rate_limit: RateLimitConfig,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RateLimitConfig {
    pub requests_per_minute: u32,
    pub burst_size: u32,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MonitoringConfig {
    pub metrics_port: u16,
    pub log_level: String,
    pub enable_tracing: bool,
}

impl AppConfig {
    pub fn load() -> Result<Self> {
        // Load default configuration
        let mut config = Self::default_config();
        
        // Override with environment variables
        config.override_from_env()?;
        
        // Load from configuration files if they exist
        if let Ok(config_content) = std::fs::read_to_string("configs/default.yaml") {
            let file_config: AppConfig = serde_yaml::from_str(&config_content)
                .context("Failed to parse default.yaml")?;
            config.merge(file_config);
        }
        
        if let Ok(config_content) = std::fs::read_to_string("configs/client_override.yaml") {
            let override_config: AppConfig = serde_yaml::from_str(&config_content)
                .context("Failed to parse client_override.yaml")?;
            config.merge(override_config);
        }
        
        Ok(config)
    }
    
    fn default_config() -> Self {
        Self {
            server: ServerConfig {
                host: "0.0.0.0".to_string(),
                port: 8000,
                workers: 4,
                max_connections: 1000,
            },
            database: DatabaseConfig {
                postgres_url: "postgresql://postgres:password@localhost:5432/kyc_db".to_string(),
                mongodb_url: "mongodb://localhost:27017/kyc_db".to_string(),
                max_connections: 10,
                connection_timeout: 30,
            },
            kafka: KafkaConfig {
                bootstrap_servers: "localhost:9092".to_string(),
                group_id: "kyc-orchestrator".to_string(),
                topics: KafkaTopics {
                    data_ingestion: "data-ingestion".to_string(),
                    kyc_analysis: "kyc-analysis-results".to_string(),
                    decision_results: "decision-results".to_string(),
                    compliance_results: "compliance-results".to_string(),
                    quality_results: "quality-results".to_string(),
                    notifications: "notifications".to_string(),
                },
                producer_config: KafkaProducerConfig {
                    acks: "all".to_string(),
                    retries: 3,
                    batch_size: 16384,
                    linger_ms: 5,
                },
                consumer_config: KafkaConsumerConfig {
                    auto_offset_reset: "earliest".to_string(),
                    enable_auto_commit: true,
                    session_timeout_ms: 30000,
                },
            },
            redis: RedisConfig {
                url: "redis://localhost:6379".to_string(),
                max_connections: 10,
                connection_timeout: 5,
                command_timeout: 5,
            },
            agents: AgentsConfig {
                data_ingestion: AgentConfig {
                    url: "http://localhost:8001".to_string(),
                    timeout: 30,
                    max_retries: 3,
                    health_check_interval: 30,
                },
                kyc_analysis: AgentConfig {
                    url: "http://localhost:8002".to_string(),
                    timeout: 60,
                    max_retries: 3,
                    health_check_interval: 30,
                },
                decision_making: AgentConfig {
                    url: "http://localhost:8003".to_string(),
                    timeout: 45,
                    max_retries: 3,
                    health_check_interval: 30,
                },
                compliance_monitoring: AgentConfig {
                    url: "http://localhost:8004".to_string(),
                    timeout: 30,
                    max_retries: 3,
                    health_check_interval: 30,
                },
                data_quality: AgentConfig {
                    url: "http://localhost:8005".to_string(),
                    timeout: 30,
                    max_retries: 3,
                    health_check_interval: 30,
                },
            },
            security: SecurityConfig {
                jwt_secret: "your-secret-key-change-in-production".to_string(),
                session_timeout: 3600,
                rate_limit: RateLimitConfig {
                    requests_per_minute: 100,
                    burst_size: 20,
                },
            },
            monitoring: MonitoringConfig {
                metrics_port: 9090,
                log_level: "info".to_string(),
                enable_tracing: true,
            },
        }
    }
    
    fn override_from_env(&mut self) -> Result<()> {
        if let Ok(host) = env::var("SERVER_HOST") {
            self.server.host = host;
        }
        
        if let Ok(port) = env::var("SERVER_PORT") {
            self.server.port = port.parse().context("Invalid SERVER_PORT")?;
        }
        
        // Handle PostgreSQL URL from environment variables
        if let Ok(postgres_url) = env::var("POSTGRES_URL") {
            self.database.postgres_url = postgres_url;
        } else {
            // Construct PostgreSQL URL from individual environment variables
            let host = env::var("POSTGRES_HOST").unwrap_or_else(|_| "localhost".to_string());
            let port = env::var("POSTGRES_PORT").unwrap_or_else(|_| "5432".to_string());
            let db = env::var("POSTGRES_DB").unwrap_or_else(|_| "kyc_db".to_string());
            let user = env::var("POSTGRES_USER").unwrap_or_else(|_| "postgres".to_string());
            let password = env::var("POSTGRES_PASSWORD").unwrap_or_else(|_| "password".to_string());
            
            self.database.postgres_url = format!(
                "postgresql://{}:{}@{}:{}/{}",
                user, password, host, port, db
            );
        }
        
        if let Ok(mongodb_url) = env::var("MONGODB_URL") {
            self.database.mongodb_url = mongodb_url;
        }
        
        if let Ok(kafka_servers) = env::var("KAFKA_BOOTSTRAP_SERVERS") {
            self.kafka.bootstrap_servers = kafka_servers;
        }
        
        if let Ok(redis_url) = env::var("REDIS_URL") {
            self.redis.url = redis_url;
        }
        
        if let Ok(jwt_secret) = env::var("JWT_SECRET") {
            self.security.jwt_secret = jwt_secret;
        }
        
        Ok(())
    }
    
    fn merge(&mut self, other: AppConfig) {
        // Merge server config
        if !other.server.host.is_empty() {
            self.server.host = other.server.host;
        }
        if other.server.port != 0 {
            self.server.port = other.server.port;
        }
        
        // Merge database config
        if !other.database.postgres_url.is_empty() {
            self.database.postgres_url = other.database.postgres_url;
        }
        if !other.database.mongodb_url.is_empty() {
            self.database.mongodb_url = other.database.mongodb_url;
        }
        
        // Merge Kafka config
        if !other.kafka.bootstrap_servers.is_empty() {
            self.kafka.bootstrap_servers = other.kafka.bootstrap_servers;
        }
        
        // Merge Redis config
        if !other.redis.url.is_empty() {
            self.redis.url = other.redis.url;
        }
        
        // Merge security config
        if !other.security.jwt_secret.is_empty() {
            self.security.jwt_secret = other.security.jwt_secret;
        }
    }
}
