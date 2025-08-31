/*!
 * Security Module
 * Authentication, authorization, and security utilities
 */

use anyhow::{Result, Context};
use jsonwebtoken::{encode, decode, Header, Algorithm, Validation, EncodingKey, DecodingKey};
use serde::{Deserialize, Serialize};
use chrono::{DateTime, Utc, Duration};
use bcrypt::{hash, verify, DEFAULT_COST};

#[derive(Debug, Serialize, Deserialize)]
pub struct Claims {
    pub sub: String,
    pub exp: i64,
    pub iat: i64,
    pub role: String,
}

#[derive(Debug, Clone)]
pub struct SecurityManager {
    jwt_secret: String,
    session_timeout: i64,
}

impl SecurityManager {
    pub fn new(jwt_secret: String, session_timeout: u64) -> Self {
        Self {
            jwt_secret,
            session_timeout: session_timeout as i64,
        }
    }
    
    pub fn generate_token(&self, user_id: &str, role: &str) -> Result<String> {
        let now = Utc::now();
        let exp = now + Duration::seconds(self.session_timeout);
        
        let claims = Claims {
            sub: user_id.to_string(),
            exp: exp.timestamp(),
            iat: now.timestamp(),
            role: role.to_string(),
        };
        
        let token = encode(
            &Header::default(),
            &claims,
            &EncodingKey::from_secret(self.jwt_secret.as_ref()),
        ).context("Failed to generate JWT token")?;
        
        Ok(token)
    }
    
    pub fn validate_token(&self, token: &str) -> Result<Claims> {
        let token_data = decode::<Claims>(
            token,
            &DecodingKey::from_secret(self.jwt_secret.as_ref()),
            &Validation::new(Algorithm::HS256),
        ).context("Failed to validate JWT token")?;
        
        Ok(token_data.claims)
    }
    
    pub fn hash_password(&self, password: &str) -> Result<String> {
        hash(password, DEFAULT_COST)
            .context("Failed to hash password")
    }
    
    pub fn verify_password(&self, password: &str, hash: &str) -> Result<bool> {
        verify(password, hash)
            .context("Failed to verify password")
    }
    
    pub fn generate_api_key(&self) -> String {
        use rand::Rng;
        const CHARSET: &[u8] = b"ABCDEFGHIJKLMNOPQRSTUVWXYZ\
                                abcdefghijklmnopqrstuvwxyz\
                                0123456789";
        const API_KEY_LEN: usize = 32;
        let mut rng = rand::thread_rng();
        
        (0..API_KEY_LEN)
            .map(|_| {
                let idx = rng.gen_range(0..CHARSET.len());
                CHARSET[idx] as char
            })
            .collect()
    }
    
    pub fn sanitize_input(&self, input: &str) -> String {
        // Basic input sanitization
        input
            .chars()
            .filter(|c| c.is_alphanumeric() || " .-_@".contains(*c))
            .collect()
    }
    
    pub fn validate_customer_id(&self, customer_id: &str) -> Result<()> {
        if customer_id.is_empty() {
            return Err(anyhow::anyhow!("Customer ID cannot be empty"));
        }
        
        if customer_id.len() > 100 {
            return Err(anyhow::anyhow!("Customer ID too long"));
        }
        
        if !customer_id.chars().all(|c| c.is_alphanumeric() || "-_".contains(c)) {
            return Err(anyhow::anyhow!("Customer ID contains invalid characters"));
        }
        
        Ok(())
    }
    
    pub fn validate_session_id(&self, session_id: &str) -> Result<()> {
        if session_id.is_empty() {
            return Err(anyhow::anyhow!("Session ID cannot be empty"));
        }
        
        // UUID format validation
        if let Err(_) = uuid::Uuid::parse_str(session_id) {
            return Err(anyhow::anyhow!("Invalid session ID format"));
        }
        
        Ok(())
    }
}
