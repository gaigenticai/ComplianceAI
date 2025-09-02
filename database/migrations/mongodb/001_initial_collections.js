// ComplianceAI MongoDB Migration
// Version: 001
// Description: Initial MongoDB collections and indexes creation
// Date: 2024-01-15
// Author: ComplianceAI Development Team

// Migration tracking collection
db.migrations.insertOne({
  version: "001",
  description: "Initial MongoDB collections and indexes creation",
  applied_at: new Date(),
  applied_by: "system",
  success: false
});

// Create collections for document storage
db.createCollection("regulatory_documents", {
  validator: {
    $jsonSchema: {
      bsonType: "object",
      required: ["document_id", "document_type", "jurisdiction", "effective_date"],
      properties: {
        document_id: {
          bsonType: "string",
          description: "Unique document identifier"
        },
        document_type: {
          enum: ["regulation", "guidance", "template", "form"],
          description: "Type of regulatory document"
        },
        jurisdiction: {
          bsonType: "string",
          description: "Regulatory jurisdiction code"
        },
        title: {
          bsonType: "string",
          description: "Document title"
        },
        effective_date: {
          bsonType: "date",
          description: "Date when document becomes effective"
        },
        expiry_date: {
          bsonType: ["date", "null"],
          description: "Date when document expires"
        },
        status: {
          enum: ["draft", "active", "superseded", "withdrawn"],
          description: "Document status"
        },
        content: {
          bsonType: "object",
          description: "Document content and metadata"
        },
        attachments: {
          bsonType: "array",
          description: "Document attachments"
        },
        tags: {
          bsonType: "array",
          description: "Document tags for search"
        },
        created_at: {
          bsonType: "date",
          description: "Document creation timestamp"
        },
        updated_at: {
          bsonType: "date",
          description: "Document last update timestamp"
        },
        created_by: {
          bsonType: "string",
          description: "User who created the document"
        },
        updated_by: {
          bsonType: "string",
          description: "User who last updated the document"
        }
      }
    }
  }
});

// Collection for parsed regulatory requirements
db.createCollection("regulatory_requirements", {
  validator: {
    $jsonSchema: {
      bsonType: "object",
      required: ["requirement_id", "document_id", "jurisdiction", "requirement_type"],
      properties: {
        requirement_id: {
          bsonType: "string",
          description: "Unique requirement identifier"
        },
        document_id: {
          bsonType: "string",
          description: "Reference to source document"
        },
        jurisdiction: {
          bsonType: "string",
          description: "Regulatory jurisdiction"
        },
        requirement_type: {
          enum: ["reporting", "capital", "liquidity", "governance", "disclosure"],
          description: "Type of regulatory requirement"
        },
        title: {
          bsonType: "string",
          description: "Requirement title"
        },
        description: {
          bsonType: "string",
          description: "Detailed requirement description"
        },
        frequency: {
          enum: ["daily", "weekly", "monthly", "quarterly", "annual", "event-driven"],
          description: "Reporting frequency"
        },
        deadline: {
          bsonType: "object",
          description: "Deadline information"
        },
        scope: {
          bsonType: "object",
          description: "Applicability scope"
        },
        validation_rules: {
          bsonType: "array",
          description: "Validation rules for compliance"
        },
        metadata: {
          bsonType: "object",
          description: "Additional metadata"
        },
        status: {
          enum: ["active", "superseded", "withdrawn"],
          description: "Requirement status"
        },
        created_at: {
          bsonType: "date",
          description: "Creation timestamp"
        },
        updated_at: {
          bsonType: "date",
          description: "Last update timestamp"
        }
      }
    }
  }
});

// Collection for JSON-Logic rule definitions
db.createCollection("compliance_rules", {
  validator: {
    $jsonSchema: {
      bsonType: "object",
      required: ["rule_id", "rule_name", "rule_logic"],
      properties: {
        rule_id: {
          bsonType: "string",
          description: "Unique rule identifier"
        },
        rule_name: {
          bsonType: "string",
          description: "Human-readable rule name"
        },
        rule_logic: {
          bsonType: "object",
          description: "JSON-Logic rule definition"
        },
        jurisdiction: {
          bsonType: ["string", "null"],
          description: "Applicable jurisdiction"
        },
        rule_type: {
          enum: ["validation", "calculation", "transformation", "alert"],
          description: "Type of compliance rule"
        },
        severity: {
          enum: ["info", "warning", "error", "critical"],
          description: "Rule violation severity"
        },
        description: {
          bsonType: "string",
          description: "Rule description"
        },
        test_cases: {
          bsonType: "array",
          description: "Test cases for rule validation"
        },
        metadata: {
          bsonType: "object",
          description: "Additional rule metadata"
        },
        status: {
          enum: ["draft", "active", "deprecated"],
          description: "Rule status"
        },
        version: {
          bsonType: "string",
          description: "Rule version"
        },
        created_at: {
          bsonType: "date",
          description: "Creation timestamp"
        },
        updated_at: {
          bsonType: "date",
          description: "Last update timestamp"
        },
        created_by: {
          bsonType: "string",
          description: "User who created the rule"
        },
        updated_by: {
          bsonType: "string",
          description: "User who last updated the rule"
        }
      }
    }
  }
});

// Collection for document parsing results
db.createCollection("document_parsing_results", {
  validator: {
    $jsonSchema: {
      bsonType: "object",
      required: ["document_id", "parsing_status"],
      properties: {
        document_id: {
          bsonType: "string",
          description: "Reference to parsed document"
        },
        parsing_status: {
          enum: ["pending", "processing", "completed", "failed"],
          description: "Parsing status"
        },
        parsing_method: {
          enum: ["ocr", "nlp", "manual", "api"],
          description: "Method used for parsing"
        },
        parsed_content: {
          bsonType: "object",
          description: "Parsed document content"
        },
        extracted_entities: {
          bsonType: "array",
          description: "Named entities extracted from document"
        },
        confidence_score: {
          bsonType: "double",
          minimum: 0.0,
          maximum: 1.0,
          description: "Confidence score of parsing accuracy"
        },
        processing_time_seconds: {
          bsonType: "double",
          description: "Time taken to process document"
        },
        error_message: {
          bsonType: ["string", "null"],
          description: "Error message if parsing failed"
        },
        metadata: {
          bsonType: "object",
          description: "Additional parsing metadata"
        },
        created_at: {
          bsonType: "date",
          description: "Parsing start timestamp"
        },
        completed_at: {
          bsonType: "date",
          description: "Parsing completion timestamp"
        }
      }
    }
  }
});

// Collection for audit trail events
db.createCollection("audit_events", {
  validator: {
    $jsonSchema: {
      bsonType: "object",
      required: ["event_id", "event_type", "entity_type", "entity_id"],
      properties: {
        event_id: {
          bsonType: "string",
          description: "Unique event identifier"
        },
        event_type: {
          enum: ["create", "update", "delete", "access", "export", "import"],
          description: "Type of audit event"
        },
        entity_type: {
          bsonType: "string",
          description: "Type of entity being audited"
        },
        entity_id: {
          bsonType: "string",
          description: "Identifier of the audited entity"
        },
        user_id: {
          bsonType: ["string", "null"],
          description: "User who performed the action"
        },
        session_id: {
          bsonType: ["string", "null"],
          description: "User session identifier"
        },
        ip_address: {
          bsonType: ["string", "null"],
          description: "IP address of the user"
        },
        user_agent: {
          bsonType: ["string", "null"],
          description: "User agent string"
        },
        old_values: {
          bsonType: "object",
          description: "Previous values before change"
        },
        new_values: {
          bsonType: "object",
          description: "New values after change"
        },
        change_reason: {
          bsonType: ["string", "null"],
          description: "Reason for the change"
        },
        compliance_impact: {
          bsonType: ["string", "null"],
          description: "Impact on regulatory compliance"
        },
        metadata: {
          bsonType: "object",
          description: "Additional event metadata"
        },
        event_timestamp: {
          bsonType: "date",
          description: "Timestamp of the event"
        },
        jurisdiction: {
          bsonType: ["string", "null"],
          description: "Regulatory jurisdiction"
        }
      }
    }
  }
});

// Collection for report templates
db.createCollection("report_templates", {
  validator: {
    $jsonSchema: {
      bsonType: "object",
      required: ["template_id", "template_name", "report_type"],
      properties: {
        template_id: {
          bsonType: "string",
          description: "Unique template identifier"
        },
        template_name: {
          bsonType: "string",
          description: "Template display name"
        },
        report_type: {
          enum: ["FINREP", "COREP", "DORA", "AML", "CUSTOM"],
          description: "Type of regulatory report"
        },
        jurisdiction: {
          bsonType: "string",
          description: "Applicable jurisdiction"
        },
        format: {
          enum: ["XBRL", "JSON", "CSV", "XML", "PDF"],
          description: "Report output format"
        },
        version: {
          bsonType: "string",
          description: "Template version"
        },
        schema_definition: {
          bsonType: "object",
          description: "Schema definition for report structure"
        },
        field_mappings: {
          bsonType: "object",
          description: "Data field mappings"
        },
        validation_rules: {
          bsonType: "array",
          description: "Template-specific validation rules"
        },
        sample_data: {
          bsonType: "object",
          description: "Sample data for testing"
        },
        metadata: {
          bsonType: "object",
          description: "Additional template metadata"
        },
        status: {
          enum: ["draft", "active", "deprecated"],
          description: "Template status"
        },
        created_at: {
          bsonType: "date",
          description: "Creation timestamp"
        },
        updated_at: {
          bsonType: "date",
          description: "Last update timestamp"
        },
        created_by: {
          bsonType: "string",
          description: "User who created the template"
        },
        updated_by: {
          bsonType: "string",
          description: "User who last updated the template"
        }
      }
    }
  }
});

// Collection for workflow definitions
db.createCollection("workflow_definitions", {
  validator: {
    $jsonSchema: {
      bsonType: "object",
      required: ["workflow_id", "workflow_name", "workflow_type"],
      properties: {
        workflow_id: {
          bsonType: "string",
          description: "Unique workflow identifier"
        },
        workflow_name: {
          bsonType: "string",
          description: "Workflow display name"
        },
        workflow_type: {
          enum: ["report_generation", "approval", "submission", "validation"],
          description: "Type of workflow"
        },
        description: {
          bsonType: "string",
          description: "Workflow description"
        },
        jurisdiction: {
          bsonType: ["string", "null"],
          description: "Applicable jurisdiction"
        },
        steps: {
          bsonType: "array",
          description: "Workflow steps definition"
        },
        triggers: {
          bsonType: "array",
          description: "Workflow trigger conditions"
        },
        notifications: {
          bsonType: "object",
          description: "Notification configuration"
        },
        sla_requirements: {
          bsonType: "object",
          description: "Service level agreement requirements"
        },
        metadata: {
          bsonType: "object",
          description: "Additional workflow metadata"
        },
        status: {
          enum: ["draft", "active", "deprecated"],
          description: "Workflow status"
        },
        version: {
          bsonType: "string",
          description: "Workflow version"
        },
        created_at: {
          bsonType: "date",
          description: "Creation timestamp"
        },
        updated_at: {
          bsonType: "date",
          description: "Last update timestamp"
        },
        created_by: {
          bsonType: "string",
          description: "User who created the workflow"
        },
        updated_by: {
          bsonType: "string",
          description: "User who last updated the workflow"
        }
      }
    }
  }
});

// Create indexes for performance
db.regulatory_documents.createIndex({ "document_id": 1 }, { unique: true });
db.regulatory_documents.createIndex({ "jurisdiction": 1 });
db.regulatory_documents.createIndex({ "document_type": 1 });
db.regulatory_documents.createIndex({ "status": 1 });
db.regulatory_documents.createIndex({ "effective_date": 1 });
db.regulatory_documents.createIndex({ "tags": 1 });
db.regulatory_documents.createIndex({ "created_at": 1 });

db.regulatory_requirements.createIndex({ "requirement_id": 1 }, { unique: true });
db.regulatory_requirements.createIndex({ "document_id": 1 });
db.regulatory_requirements.createIndex({ "jurisdiction": 1 });
db.regulatory_requirements.createIndex({ "requirement_type": 1 });
db.regulatory_requirements.createIndex({ "status": 1 });
db.regulatory_requirements.createIndex({ "created_at": 1 });

db.compliance_rules.createIndex({ "rule_id": 1 }, { unique: true });
db.compliance_rules.createIndex({ "jurisdiction": 1 });
db.compliance_rules.createIndex({ "rule_type": 1 });
db.compliance_rules.createIndex({ "severity": 1 });
db.compliance_rules.createIndex({ "status": 1 });
db.compliance_rules.createIndex({ "created_at": 1 });

db.document_parsing_results.createIndex({ "document_id": 1 });
db.document_parsing_results.createIndex({ "parsing_status": 1 });
db.document_parsing_results.createIndex({ "created_at": 1 });

db.audit_events.createIndex({ "event_id": 1 }, { unique: true });
db.audit_events.createIndex({ "event_type": 1 });
db.audit_events.createIndex({ "entity_type": 1, "entity_id": 1 });
db.audit_events.createIndex({ "user_id": 1 });
db.audit_events.createIndex({ "event_timestamp": 1 });
db.audit_events.createIndex({ "jurisdiction": 1 });

db.report_templates.createIndex({ "template_id": 1 }, { unique: true });
db.report_templates.createIndex({ "report_type": 1 });
db.report_templates.createIndex({ "jurisdiction": 1 });
db.report_templates.createIndex({ "status": 1 });
db.report_templates.createIndex({ "created_at": 1 });

db.workflow_definitions.createIndex({ "workflow_id": 1 }, { unique: true });
db.workflow_definitions.createIndex({ "workflow_type": 1 });
db.workflow_definitions.createIndex({ "jurisdiction": 1 });
db.workflow_definitions.createIndex({ "status": 1 });
db.workflow_definitions.createIndex({ "created_at": 1 });

// Create capped collections for high-frequency data
db.createCollection("system_metrics", {
  capped: true,
  size: 104857600,  // 100MB
  max: 10000
});

db.createCollection("performance_logs", {
  capped: true,
  size: 524288000,  // 500MB
  max: 50000
});

// Insert sample data for testing (optional)
db.regulatory_documents.insertOne({
  document_id: "SAMPLE_REG_001",
  document_type: "regulation",
  jurisdiction: "EU",
  title: "Sample EU Regulation",
  effective_date: new Date("2024-01-01"),
  status: "active",
  content: {
    summary: "Sample regulatory document for testing",
    sections: ["Article 1", "Article 2", "Article 3"]
  },
  tags: ["sample", "testing", "eu"],
  created_at: new Date(),
  created_by: "system"
});

// Update migration status
db.migrations.updateOne(
  { version: "001" },
  {
    $set: {
      success: true,
      checksum: "mongodb-initial-collections-checksum"
    }
  }
);

// Print completion message
print("MongoDB migration 001 completed successfully");
print("Created collections:");
print("- regulatory_documents");
print("- regulatory_requirements");
print("- compliance_rules");
print("- document_parsing_results");
print("- audit_events");
print("- report_templates");
print("- workflow_definitions");
print("- system_metrics (capped)");
print("- performance_logs (capped)");
print("Created indexes for all collections");
print("Inserted sample data for testing");
