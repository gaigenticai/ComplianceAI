use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use anyhow::Result;

/// Main configuration structure for the KYC automation platform
/// Loads from default.yaml and merges with client_override.yaml
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Config {
    /// Server configuration
    pub server: ServerConfig,
    /// Kafka messaging configuration
    pub kafka: KafkaConfig,
    /// Pinecone vector database configuration
    pub pinecone: PineconeConfig,
    /// Agent service endpoints
    pub agents: AgentConfig,
    /// Authentication settings
    pub auth: AuthConfig,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ServerConfig {
    /// Server host address
    pub host: String,
    /// Server port (with automatic conflict resolution)
    pub port: u16,
    /// Maximum file upload size in bytes
    pub max_file_size: usize,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct KafkaConfig {
    /// Kafka broker addresses
    pub brokers: String,
    /// Topic for KYC requests
    pub kyc_request_topic: String,
    /// Topic for KYC results
    pub kyc_result_topic: String,
    /// Topic for feedback collection
    pub kyc_feedback_topic: String,
    /// Consumer group ID for orchestrator
    pub consumer_group: String,
    /// Consumer group ID for result consumer
    pub result_consumer_group: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PineconeConfig {
    /// Pinecone API key (or local emulator endpoint)
    pub api_key: String,
    /// Pinecone environment
    pub environment: String,
    /// Index name for KYC data
    pub index_name: String,
    /// Pinecone project ID
    pub project_id: Option<String>,
    /// Vector dimension
    pub dimension: usize,
    /// Pinecone host URL (optional, will construct if not provided)
    #[serde(default)]
    pub host: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AgentConfig {
    /// OCR agent endpoint
    pub ocr_agent: String,
    /// Face recognition agent endpoint
    pub face_agent: String,
    /// Watchlist screening agent endpoint
    pub watchlist_agent: String,
    /// Data integration agent endpoint
    pub data_integration_agent: String,
    /// Quality assurance agent endpoint
    pub qa_agent: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AuthConfig {
    /// Whether authentication is required
    pub require_auth: bool,
    /// JWT secret key
    pub jwt_secret: String,
    /// Session timeout in hours
    pub session_timeout: u64,
}

impl Config {
    /// Load configuration from default.yaml and merge with client_override.yaml
    /// This allows clients to override specific settings without modifying core config
    pub fn load() -> Result<Self> {
        // Load default configuration
        let default_config_path = "configs/default.yaml";
        let default_content = std::fs::read_to_string(default_config_path)
            .map_err(|e| anyhow::anyhow!("Failed to read default config: {}", e))?;
        
        // Temporarily disable environment variable expansion for debugging
        let expanded_content = default_content;
        
        let mut config: Config = serde_yaml::from_str(&expanded_content)
            .map_err(|e| anyhow::anyhow!("Failed to parse default config: {}", e))?;

        // Try to load client override configuration
        let override_config_path = "configs/client_override.yaml";
        if std::path::Path::new(override_config_path).exists() {
            let override_content = std::fs::read_to_string(override_config_path)
                .map_err(|e| anyhow::anyhow!("Failed to read override config: {}", e))?;
            
            if !override_content.trim().is_empty() {
                let override_config: serde_yaml::Value = serde_yaml::from_str(&override_content)
                    .map_err(|e| anyhow::anyhow!("Failed to parse override config: {}", e))?;
                
                // Merge override config into default config
                config = merge_configs(config, override_config)?;
            }
        }

        // Load environment variables
        if let Ok(require_auth) = std::env::var("REQUIRE_AUTH") {
            config.auth.require_auth = require_auth.to_lowercase() == "true";
        }

        // Resolve port conflicts automatically
        config.server.port = find_available_port(config.server.port)?;

        Ok(config)
    }
}

/// Expand environment variables in configuration content
/// Replaces ${VAR_NAME} with the value of the environment variable
fn expand_env_vars(content: &str) -> Result<String> {
    let mut result = content.to_string();
    
    // Find all ${VAR_NAME} patterns and replace them
    let re = regex::Regex::new(r"\$\{([^}]+)\}").unwrap();
    
    for cap in re.captures_iter(content) {
        let full_match = &cap[0];
        let var_name = &cap[1];
        
        match std::env::var(var_name) {
            Ok(value) => {
                result = result.replace(full_match, &value);
            }
            Err(_) => {
                return Err(anyhow::anyhow!("Environment variable {} not found", var_name));
            }
        }
    }
    
    Ok(result)
}

/// Merge override configuration into base configuration
/// This allows selective overriding of configuration values
fn merge_configs(mut base: Config, override_val: serde_yaml::Value) -> Result<Config> {
    if let serde_yaml::Value::Mapping(override_map) = override_val {
        let base_yaml = serde_yaml::to_value(&base)?;
        let merged = merge_yaml_values(base_yaml, serde_yaml::Value::Mapping(override_map));
        base = serde_yaml::from_value(merged)?;
    }
    Ok(base)
}

/// Recursively merge YAML values, with override taking precedence
fn merge_yaml_values(base: serde_yaml::Value, override_val: serde_yaml::Value) -> serde_yaml::Value {
    match (base, override_val) {
        (serde_yaml::Value::Mapping(mut base_map), serde_yaml::Value::Mapping(override_map)) => {
            for (key, value) in override_map {
                if let Some(base_value) = base_map.get(&key) {
                    base_map.insert(key, merge_yaml_values(base_value.clone(), value));
                } else {
                    base_map.insert(key, value);
                }
            }
            serde_yaml::Value::Mapping(base_map)
        }
        (_, override_val) => override_val,
    }
}



/// Find an available port starting from the given port number
/// This ensures automatic port conflict resolution as required by the rules
fn find_available_port(start_port: u16) -> Result<u16> {
    use std::net::{TcpListener, SocketAddr};
    
    for port in start_port..start_port + 100 {
        let addr = SocketAddr::from(([127, 0, 0, 1], port));
        if TcpListener::bind(addr).is_ok() {
            log::info!("Found available port: {}", port);
            return Ok(port);
        }
    }
    
    Err(anyhow::anyhow!("No available ports found in range {}-{}", start_port, start_port + 100))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_port_conflict_resolution() {
        let port = find_available_port(8000).unwrap();
        assert!(port >= 8000);
        assert!(port < 8100);
    }

    #[test]
    fn test_yaml_merge() {
        let base = serde_yaml::from_str(r#"
            server:
              host: "localhost"
              port: 8000
            kafka:
              brokers: "localhost:9092"
        "#).unwrap();
        
        let override_val = serde_yaml::from_str(r#"
            server:
              port: 8080
            kafka:
              brokers: "kafka:9092"
        "#).unwrap();
        
        let merged = merge_yaml_values(base, override_val);
        let config: Config = serde_yaml::from_value(merged).unwrap();
        
        assert_eq!(config.server.host, "localhost");
        assert_eq!(config.server.port, 8080);
        assert_eq!(config.kafka.brokers, "kafka:9092");
    }
}
