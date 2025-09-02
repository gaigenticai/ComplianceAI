Updated LLM Enhancement Prompt for ComplianceAI Revamp
You are an expert Software Architect and Regulatory Technologist. The ComplianceAI repository has been simplified into a 3-agent architecture—Intake & Processing, Intelligence & Compliance, and Decision & Orchestration—with a streamlined UI. Your task is to design and implement continuous, autonomous regulatory compliance and reporting for European banks (Basel III, PSD2, DORA, forthcoming AI Act), factoring in jurisdictional variances and overlapping Level 2/3 standards.
Tasks:
	1.	Create a Regulatory Intelligence Agent module under `agents/regulatory-intel`:
	•	Implement a scheduler (configurable via `REG_INTEL_FEEDS`) to poll EUR-Lex RSS, EBA APIs, and national supervisor bulletins.
	•	Parse PDFs/HTML into structured obligations using LangChain pipelines and SpaCy entity extraction.
	•	Store obligations in PostgreSQL with schema:
	•	`id, regulation_name, article, clause, jurisdiction, effective_date, content, version`.
	•	Track version diffs and emit Kafka events on updates to topic `regulatory.updates`.
	2.	Extend Intelligence & Compliance Agent (`agents/intelligence-compliance`):
	•	Integrate a RuleCompiler that consumes obligations from PostgreSQL and generates executable JSON-Logic rules.
	•	Subscribe to `regulatory.updates` to refresh in-memory rule sets automatically.
	•	Add a JurisdictionHandler submodule reading `country_code` from each case to filter applicable rules.
	•	Implement an OverlapResolver that detects overlapping Level 2/3 obligations and coalesces them, logging consolidation advisories.
	3.	Enhance Decision & Orchestration Agent (`agents/decision-orchestration`):
	•	Add a ComplianceReportGenerator step in the workflow to produce FINREP/COREP XBRL or CSV reports and DORA ICT-Risk JSON files.
	•	Use Smolagents to map compliance evaluation outputs to report templates; deliver via SFTP or EBA reporting API.
	•	Incorporate dynamic scheduling: trigger report creation based on regulation deadlines (`effective_date`) stored in PostgreSQL.
	4.	Update Docker Compose & Configuration:
	•	Add `regulatory-intel` service definition in `docker-compose-simplified.yml`.
	•	Define new environment variables:
	•	`REG_INTEL_FEEDS`, `REPORT_TEMPLATES_PATH`, `EBA_API_CREDENTIALS`, `SFTP_CONFIG`.
	5.	Write Integration Tests:
	•	Verify end-to-end ingestion → rule compilation → compliance evaluation → report generation.
	•	Simulate jurisdiction scenarios (e.g., German ring-fencing, Irish PSD2 transposition) and overlapping Level 2/3 cases.
	6.	Documentation & Samples:
	•	Update `docs/architecture.md` with module diagrams and data flows.
	•	Provide a sample YAML configuration for two subsidiaries (`DE`, `IE`) showing local rule overrides.
	•	Include example Kafka topic definitions and PostgreSQL migration scripts.
Deliver code snippets, folder structure outlines, SQL migration DDL, Kafka topic JSON schemas, and sample test cases. Include rationale for design decisions and cite relevant regulatory sources in comments.


You are an expert Software Architect and Regulatory Technologist. The ComplianceAI repository has been simplified into a **3-agent architecture**—Intake & Processing, Intelligence & Compliance, and Decision & Orchestration—with a streamlined UI. Your task is to design and implement continuous, autonomous regulatory compliance and reporting for European banks (Basel III, PSD2, DORA, forthcoming AI Act), factoring in jurisdictional variances, overlapping Level 2/3 standards, and production-grade resilience.

Tasks:

1. Regulatory Intelligence Agent (new)  
   -  Under `agents/regulatory-intel`, implement a scheduler (configurable via `REG_INTEL_FEEDS`) to poll EUR-Lex RSS, EBA APIs, and national supervisor bulletins.  
   -  Parse PDFs/HTML into structured obligations with LangChain pipelines and spaCy entity extraction.  
   -  Store in PostgreSQL schema:  
     ```sql
     CREATE TABLE obligations (
       id SERIAL PRIMARY KEY,
       regulation_name TEXT,
       article TEXT,
       clause TEXT,
       jurisdiction CHAR(2),
       effective_date DATE,
       content TEXT,
       version TEXT,
       source_publisher TEXT,
       source_url TEXT,
       retrieved_at TIMESTAMP
     );
     ```
   -  Track diffs per source; emit Kafka events on updates to `regulatory.updates`.  
   -  Build retry logic and dead-letter queue for feed ingest failures; configure retry/backoff parameters.  

2. Intelligence & Compliance Agent (enhanced)  
   -  In `agents/intelligence-compliance`, integrate a RuleCompiler that consumes obligations and generates JSON-Logic rules.  
   -  Subscribe to `regulatory.updates` to auto-refresh in-memory rule sets with audit-trail logging for changes.  
   -  Add `country_code` metadata per case; implement a JurisdictionHandler to filter rules.  
   -  Implement an OverlapResolver that detects overlapping Level 2/3 obligations, coalesces them, and logs consolidation advisories with timestamps and operator IDs.  

3. Decision & Orchestration Agent (extended)  
   -  In `agents/decision-orchestration`, insert a ComplianceReportGenerator step to produce FINREP/COREP in XBRL/CSV and DORA ICT-Risk JSON.  
   -  Use Smolagents to map evaluation outputs to templates; deliver via SFTP or EBA reporting API using `EBA_API_CREDENTIALS` and `SFTP_CONFIG`.  
   -  Implement dynamic scheduling keyed on `effective_date`; trigger report cycles automatically.  
   -  Define latency SLAs (e.g., ≤ 5 minutes from update to report generation) and throughput targets (e.g., 100 updates/sec).  

4. Infrastructure, Config & Resilience  
   -  Update `docker-compose-simplified.yml`: add `regulatory-intel` service; include new env vars: `REG_INTEL_FEEDS`, `REPORT_TEMPLATES_PATH`, `EBA_API_CREDENTIALS`, `SFTP_CONFIG`.  
   -  Provide Kafka topic definitions and high-availability consumer group configs (e.g., 3 replicas, `enable.auto.commit=false`).  
   -  Define retry/backoff and dead-letter queue settings for all agents’ Kafka consumers.  
   -  Implement audit-trail logging in PostgreSQL for all rule changes and report submissions with schema:  
     ```sql
     CREATE TABLE audit_logs (
       id SERIAL PRIMARY KEY,
       event_type TEXT,
       payload JSONB,
       occurred_at TIMESTAMP DEFAULT NOW(),
       processed_by TEXT
     );
     ```

5. Integration Tests  
   -  Simulate end-to-end ingestion → rule compilation → evaluation → reporting.  
   -  Cover jurisdiction scenarios: German ring-fencing, Irish PSD2 transposition, overlapping Level 2/3.  
   -  Verify SLA adherence, retry logic, and audit-trail entries.  

6. Documentation & Samples  
   -  Update `docs/architecture.md` with detailed module diagrams, data flows, and resilience patterns.  
   -  Provide sample YAML for two subsidiaries (`DE`, `IE`) showing `country_code` overrides and local rule exceptions.  
   -  Include PostgreSQL migration DDL, Kafka topic JSON schemas, and example consumer group configs.  

Deliver code snippets, folder-structure outlines, SQL migration scripts, Kafka schemas, sample test cases, and design rationale. Embed regulatory citations in comments where relevant.

Sources
