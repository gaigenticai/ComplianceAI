// MongoDB Database Initialization Script
// This script sets up the initial MongoDB structure and data

// Switch to the KYC database
db = db.getSiblingDB('kyc_db');

// Create application user with proper permissions
db.createUser({
  user: 'kyc_app',
  pwd: 'kyc_app_password',
  roles: [
    {
      role: 'readWrite',
      db: 'kyc_db'
    }
  ]
});

// Create collections with validation schemas

// Customer Data Collection
db.createCollection('customers', {
  validator: {
    $jsonSchema: {
      bsonType: 'object',
      required: ['customer_id', 'data'],
      properties: {
        customer_id: {
          bsonType: 'string',
          description: 'Customer ID is required and must be a string'
        },
        data: {
          bsonType: 'object',
          description: 'Customer data object is required'
        },
        created_at: {
          bsonType: 'date',
          description: 'Creation timestamp'
        },
        updated_at: {
          bsonType: 'date',
          description: 'Last update timestamp'
        }
      }
    }
  }
});

// Document Storage Collection
db.createCollection('documents', {
  validator: {
    $jsonSchema: {
      bsonType: 'object',
      required: ['customer_id', 'document_type', 'content'],
      properties: {
        customer_id: {
          bsonType: 'string',
          description: 'Customer ID is required'
        },
        document_type: {
          bsonType: 'string',
          enum: ['identity', 'address', 'financial', 'other'],
          description: 'Document type must be one of the enum values'
        },
        content: {
          bsonType: 'object',
          description: 'Document content is required'
        },
        metadata: {
          bsonType: 'object',
          description: 'Document metadata'
        },
        created_at: {
          bsonType: 'date',
          description: 'Creation timestamp'
        }
      }
    }
  }
});

// Processing Cache Collection
db.createCollection('processing_cache', {
  validator: {
    $jsonSchema: {
      bsonType: 'object',
      required: ['session_id', 'cache_key', 'cache_data'],
      properties: {
        session_id: {
          bsonType: 'string',
          description: 'Session ID is required'
        },
        cache_key: {
          bsonType: 'string',
          description: 'Cache key is required'
        },
        cache_data: {
          bsonType: 'object',
          description: 'Cached data is required'
        },
        expires_at: {
          bsonType: 'date',
          description: 'Cache expiration timestamp'
        },
        created_at: {
          bsonType: 'date',
          description: 'Creation timestamp'
        }
      }
    }
  }
});

// Agent Results Collection
db.createCollection('agent_results', {
  validator: {
    $jsonSchema: {
      bsonType: 'object',
      required: ['session_id', 'agent_name', 'result_data'],
      properties: {
        session_id: {
          bsonType: 'string',
          description: 'Session ID is required'
        },
        agent_name: {
          bsonType: 'string',
          enum: ['data-ingestion', 'kyc-analysis', 'decision-making', 'compliance-monitoring', 'data-quality'],
          description: 'Agent name must be one of the valid agents'
        },
        result_data: {
          bsonType: 'object',
          description: 'Agent result data is required'
        },
        processing_time: {
          bsonType: 'number',
          minimum: 0,
          description: 'Processing time in seconds'
        },
        created_at: {
          bsonType: 'date',
          description: 'Creation timestamp'
        }
      }
    }
  }
});

// ML Models Collection
db.createCollection('ml_models', {
  validator: {
    $jsonSchema: {
      bsonType: 'object',
      required: ['model_name', 'model_type', 'model_data'],
      properties: {
        model_name: {
          bsonType: 'string',
          description: 'Model name is required'
        },
        model_type: {
          bsonType: 'string',
          enum: ['risk_scoring', 'anomaly_detection', 'classification', 'regression'],
          description: 'Model type must be one of the enum values'
        },
        model_data: {
          bsonType: 'object',
          description: 'Model data and parameters'
        },
        version: {
          bsonType: 'string',
          description: 'Model version'
        },
        accuracy: {
          bsonType: 'number',
          minimum: 0,
          maximum: 1,
          description: 'Model accuracy score'
        },
        created_at: {
          bsonType: 'date',
          description: 'Creation timestamp'
        },
        updated_at: {
          bsonType: 'date',
          description: 'Last update timestamp'
        }
      }
    }
  }
});

// Create indexes for performance
db.customers.createIndex({ 'customer_id': 1 }, { unique: true });
db.customers.createIndex({ 'created_at': -1 });
db.customers.createIndex({ 'data.personal_info.email': 1 });

db.documents.createIndex({ 'customer_id': 1 });
db.documents.createIndex({ 'document_type': 1 });
db.documents.createIndex({ 'created_at': -1 });

db.processing_cache.createIndex({ 'session_id': 1 });
db.processing_cache.createIndex({ 'cache_key': 1 });
db.processing_cache.createIndex({ 'expires_at': 1 }, { expireAfterSeconds: 0 });

db.agent_results.createIndex({ 'session_id': 1 });
db.agent_results.createIndex({ 'agent_name': 1 });
db.agent_results.createIndex({ 'created_at': -1 });

db.ml_models.createIndex({ 'model_name': 1, 'version': 1 }, { unique: true });
db.ml_models.createIndex({ 'model_type': 1 });
db.ml_models.createIndex({ 'accuracy': -1 });

// Insert initial system data
db.customers.insertOne({
  customer_id: 'SYSTEM_INIT',
  data: {
    system_info: {
      initialized_at: new Date(),
      version: '1.0.0',
      description: 'System initialization marker'
    }
  },
  created_at: new Date(),
  updated_at: new Date()
});

// Insert sample ML models configuration
db.ml_models.insertMany([
  {
    model_name: 'risk_scoring_v1',
    model_type: 'risk_scoring',
    model_data: {
      algorithm: 'random_forest',
      features: ['income', 'age', 'employment_status', 'credit_score'],
      parameters: {
        n_estimators: 100,
        max_depth: 10,
        min_samples_split: 2
      }
    },
    version: '1.0.0',
    accuracy: 0.85,
    created_at: new Date(),
    updated_at: new Date()
  },
  {
    model_name: 'anomaly_detection_v1',
    model_type: 'anomaly_detection',
    model_data: {
      algorithm: 'isolation_forest',
      features: ['transaction_amount', 'transaction_frequency', 'location'],
      parameters: {
        contamination: 0.1,
        n_estimators: 100
      }
    },
    version: '1.0.0',
    accuracy: 0.78,
    created_at: new Date(),
    updated_at: new Date()
  }
]);

// Create system configuration collection
db.createCollection('system_config');
db.system_config.createIndex({ 'config_key': 1 }, { unique: true });

// Insert system configuration
db.system_config.insertMany([
  {
    config_key: 'mongodb.version',
    config_value: '1.0.0',
    config_type: 'database',
    description: 'MongoDB schema version',
    created_at: new Date(),
    updated_at: new Date()
  },
  {
    config_key: 'cache.default_ttl',
    config_value: 3600,
    config_type: 'cache',
    description: 'Default cache TTL in seconds',
    created_at: new Date(),
    updated_at: new Date()
  },
  {
    config_key: 'ml_models.auto_update',
    config_value: true,
    config_type: 'ml',
    description: 'Enable automatic model updates',
    created_at: new Date(),
    updated_at: new Date()
  }
]);

print('MongoDB initialization completed successfully');
print('Created collections: customers, documents, processing_cache, agent_results, ml_models, system_config');
print('Created user: kyc_app with readWrite permissions');
print('Created indexes for optimal performance');
