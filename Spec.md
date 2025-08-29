You are Sonnet 4, an AI IDE assistant. Generate a complete Agentic KYC Automation platform for BFSI, combining Rust for orchestration and UI, Python for specialized AI/ML tasks, and a minimal web UI for end-to-end testing. Everything must be Dockerized, configuration-driven, and modular so clients can swap in their own modules without core code changes.

1. Project Layout:
   /kyc-agent/
     ├── rust-core/                          # Rust orchestration, messaging, UI
     │    ├── Dockerfile
     │    ├── Cargo.toml
     │    ├── src/
     │    │    ├── main.rs                   # Actix-Web HTTP server & UI routes
     │    │    ├── orchestrator.rs           # Async Kafka consumer/producer via rdkafka
     │    │    ├── config.rs                 # Load default + client_override YAML via serde_yaml
     │    │    ├── messaging.rs              # Kafka producer/consumer wrapper
     │    │    ├── storage.rs                # Pinecone client wrapper
     │    │    └── ui/
     │    │          ├── templates/
     │    │          │    └── index.html     # Tera template: upload form & result display
     │    │          └── static/             # CSS/JS assets
     │    └── default.yaml                   # Default service endpoints, Kafka topics, Pinecone
     ├── python-agents/                      # Specialized AI/ML agents
     │    ├── ocr-agent/
     │    │    ├── Dockerfile
     │    │    ├── requirements.txt
     │    │    └── ocr_service.py            # FastAPI endpoint: runs pytesseract, returns {name,dob,id_number}
     │    ├── face-agent/
     │    │    ├── Dockerfile
     │    │    ├── requirements.txt
     │    │    └── face_service.py           # FastAPI endpoint: facial recognition & liveness detection, returns match_score
     │    ├── watchlist-agent/
     │    │    ├── Dockerfile
     │    │    ├── requirements.txt
     │    │    └── watchlist_service.py      # FastAPI endpoint: loads CSV/DB watchlist, returns flag & matches
     │    ├── data-integration-agent/
     │    │    ├── Dockerfile
     │    │    ├── requirements.txt
     │    │    └── data_integration_service.py   # FastAPI: integrates external APIs (sanctions, credit bureau), returns enriched data
     │    └── quality-assurance-agent/
     │         ├── Dockerfile
     │         ├── requirements.txt
     │         └── qa_service.py             # FastAPI: validates outputs against policies, returns QA verdict or exceptions
     ├── configs/
     │    ├── default.yaml                   # YAML: OCR, face, watchlist, data-integration, QA endpoints, topics, indexes
     │    └── client_override.yaml           # Empty template for client-specific overrides
     ├── docker-compose.yml                  # Orchestrates rust-core, python-agents, Kafka, Pinecone emulator
     └── README.md                           # Build/run instructions, override guide, UI usage

2. Rust Core Orchestration & UI:
   - main.rs:
     • Actix-Web server on :8000  
     • GET “/”: renders index.html form to upload ID doc & selfie  
     • POST “/submit”: saves uploads, produces “kyc_request” to Kafka, awaits “kyc_result”, returns JSON or renders result page  
     • POST “/feedback”: accepts human feedback, publishes to “kyc_feedback” for continuous learning  
   - orchestrator.rs:
     • Kafka consumer for “kyc_request”  
     • Workflow orchestration per operational_framework:
       1. Document Verification Agent  
       2. Identity Authentication Agent  
       3. Data Integration Agent  
       4. Risk Assessment Agent  
       5. Compliance Monitoring Agent  
       6. Quality Assurance Agent  
     • Aggregates responses, indexes in Pinecone, produces “kyc_result”  
   - messaging.rs: rdkafka wrapper for producer/consumer  
   - storage.rs: rust-pinecone client wrapper  
   - config.rs: loads default.yaml + merges client_override.yaml  
   - ui/templates/index.html:
     • Bootstrap form: file inputs for ID & selfie  
     • Displays executive summary, detailed analysis, audit trail, actionable insights from “kyc_result”  
     • “Provide Feedback” form posting to /feedback  
   - ui/static/: minimal CSS/JS

3. Python Agent Implementation:
   - All agents use FastAPI, exposing POST “/process” (or specific routes)  
   - OCR Agent: uses pytesseract, Pillow, returns extracted fields  
   - Face Agent: uses face-recognition/OpenCV, returns match_score & liveness verdict  
   - Watchlist Agent: loads CSV/DB, uses fuzzywuzzy for name match  
   - Data Integration Agent: configurable connectors for REST/GraphQL data sources  
   - QA Agent: runs rule-based checks, schema validation, returns QA status  

4. Docker & Orchestration:
   - Each service has its own Dockerfile, based on python:3.11-slim for agents, rust:1.69-slim for core  
   - docker-compose.yml includes:
     • rust-core  
     • ocr-agent, face-agent, watchlist-agent, data-integration-agent, qa-agent  
     • kafka (confluentinc/cp-kafka)  
     • pinecone-local emulator  
     • Networks, volumes for configs and templates  

5. Configuration & Extensibility:
   - default.yaml defines all endpoints, topics, Pinecone index names  
   - client_override.yaml allows clients to override any module URL, topics, indexes  
   - README.md:
     • `docker-compose up --build`  
     • Access UI at http://localhost:8000  
     • How to override modules in configs/client_override.yaml  
     • How to add new agents: place Python or Rust service, update config  

6. Output Requirements:
   - “kyc_result” message must include:
     • EXECUTIVE SUMMARY: recommendation (APPROVE/CONDITIONAL/ESCALATE/REJECT), risk_score, confidence, processing_time, cost_savings  
     • DETAILED ANALYSIS: OCR data & scores, biometric match, watchlist hits, data-integration insights, risk profiles, compliance check results  
     • AUDIT TRAIL: timestamps, agent calls, data sources, rule checklist  
     • ACTIONABLE INSIGHTS: follow-up actions, monitoring requirements, process improvements  
     • QA VERDICT: QA status and any exceptions

7. Compliance & Ethics:
   - All data transmitted encrypted (TLS)  
   - GDPR/PCI-DSS compliant storage by default  
   - Full explainability: include reasoning from each agent in result  
   - Ensure fair, unbiased processing and human oversight for high-risk cases  

8. Continuous Learning:
   - /feedback endpoint collects human review  
   - Feedback messages published to “kyc_feedback” Kafka topic for downstream model retraining

Ensure code is clean, modular, documented, and Docker-compliant. Provide clear logging, error handling, and health checks for all services. This prompt will generate a fully working, end-to-end Agentic KYC platform demonstrating true agentic AI capabilities.```
