/*!
 * Agent Client
 * HTTP client for communicating with AI agents
 */

use anyhow::{Result, Context};
use reqwest::Client;
use serde_json::Value;
use std::time::Duration;
use tracing::{debug, error};

use crate::config::AgentConfig;

pub struct AgentClient {
    name: String,
    base_url: String,
    client: Client,
    config: AgentConfig,
}

impl AgentClient {
    pub async fn new(name: &str, config: &AgentConfig) -> Result<Self> {
        let client = Client::builder()
            .timeout(Duration::from_secs(config.timeout))
            .build()
            .context("Failed to create HTTP client")?;
        
        Ok(Self {
            name: name.to_string(),
            base_url: config.url.clone(),
            client,
            config: config.clone(),
        })
    }
    
    pub async fn call_agent(&self, endpoint: &str, payload: &Value) -> Result<Value> {
        let url = format!("{}{}", self.base_url, endpoint);
        debug!("Calling agent {} at {}", self.name, url);
        
        let mut retries = 0;
        let max_retries = self.config.max_retries;
        
        loop {
            match self.client
                .post(&url)
                .json(payload)
                .send()
                .await
            {
                Ok(response) => {
                    if response.status().is_success() {
                        match response.json::<Value>().await {
                            Ok(result) => {
                                debug!("Agent {} call successful", self.name);
                                return Ok(result);
                            }
                            Err(e) => {
                                error!("Failed to parse response from agent {}: {}", self.name, e);
                                if retries >= max_retries {
                                    return Err(anyhow::anyhow!("Failed to parse response: {}", e));
                                }
                            }
                        }
                    } else {
                        error!("Agent {} returned error status: {}", self.name, response.status());
                        if retries >= max_retries {
                            return Err(anyhow::anyhow!("Agent returned error status: {}", response.status()));
                        }
                    }
                }
                Err(e) => {
                    error!("Failed to call agent {}: {}", self.name, e);
                    if retries >= max_retries {
                        return Err(anyhow::anyhow!("Failed to call agent: {}", e));
                    }
                }
            }
            
            retries += 1;
            tokio::time::sleep(Duration::from_millis(1000 * retries as u64)).await;
        }
    }
    
    pub async fn health_check(&self) -> Result<bool> {
        let url = format!("{}/health", self.base_url);
        
        match self.client
            .get(&url)
            .timeout(Duration::from_secs(5))
            .send()
            .await
        {
            Ok(response) => Ok(response.status().is_success()),
            Err(_) => Ok(false),
        }
    }
}
