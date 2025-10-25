# AURA Monolith File Structure with File Responsibilities

## Root Directory Structure
```
aura-underwriting/
├── README.md                    # Project overview, setup instructions, and usage guide
├── Dockerfile                   # Container configuration for deployment
├── docker-compose.yml          # Local development environment setup with dependencies
├── requirements.txt            # Python dependencies for pip installation
├── pyproject.toml              # Modern Python project configuration (Black, isort, pytest)
├── .env.example                # Template environment variables file
├── .gitignore                  # Version control ignore patterns
├── .github/                    # GitHub workflows and templates
│   └── workflows/              # CI/CD pipeline definitions
├── scripts/                    # Deployment and maintenance scripts
│   ├── start.sh               # Application startup script
│   ├── migrate.sh             # Database migration script
│   └── seed_data.sh           # Test/demo data seeding script
├── config/                     # Application configuration management
│   ├── settings.py            # Main configuration aggregator and validation
│   ├── database.py            # Database connection settings and pool configuration
│   ├── logging.py             # Centralized logging configuration (formatters, handlers)
│   └── environments/          # Environment-specific configurations
│       ├── development.py     # Dev settings (debug mode, local DB, loose security)
│       ├── staging.py         # Staging settings (production-like but with test data)
│       └── production.py      # Production settings (optimized, secure, monitored)
├── migrations/                 # Database schema version control
│   ├── alembic.ini           # Alembic configuration for migrations
│   ├── env.py                # Migration environment setup and connection logic
│   └── versions/             # Individual migration files (auto-generated)
├── tests/                      # Comprehensive test suite
│   ├── conftest.py           # Pytest configuration, fixtures, and test utilities
│   ├── unit/                 # Fast, isolated unit tests for individual functions
│   ├── integration/          # Tests for component interactions and external services
│   └── e2e/                  # End-to-end workflow tests simulating real user journeys
├── docs/                      # Project documentation
│   ├── api/                  # API documentation (OpenAPI specs, endpoint docs)
│   ├── architecture/         # System design, data flow, and technical decisions
│   └── deployment/           # Infrastructure, monitoring, and operational guides
└── src/                      # Main application source code
    └── aura/                # Core application package
        ├── __init__.py      # Package initialization and version info
        ├── main.py          # FastAPI application entry point and startup logic
        ├── shared/          # Cross-module shared infrastructure and utilities
        ├── data_infrastructure/    # Team 1: Storage, data lake, warehouse, caching
        ├── data_collection/        # Team 2: Document uploads, forms, user APIs
        ├── processing_engine/      # Team 3: Processors, external integrations, factors
        ├── ai_decision/           # Team 4: ML models, RAG, decision generation
        ├── business_rules/        # Team 5: Validation rules, compliance, thresholds
        └── workflow_orchestration/ # Team 6: Event bus, state machine, monitoring
```

## Core Application Structure (`src/aura/`)

### Main Application Entry Point
```
src/aura/
├── __init__.py                 # Package metadata, version info, and module exports
├── main.py                     # FastAPI app creation, middleware setup, router registration
├── app.py                      # Application factory pattern, dependency injection setup
├── dependencies.py             # Shared dependency injection providers (DB, auth, services)
└── middleware.py               # Custom middleware (request logging, error handling, CORS)
```

### Shared Infrastructure (`src/aura/shared/`) - Foundation Layer
```
shared/
├── __init__.py                 # Shared module exports and common imports
├── models/                     # SQLAlchemy database models (shared across all teams)
│   ├── __init__.py            # Model registry and common base classes
│   ├── base.py                # Base model with common fields (id, created_at, updated_at)
│   ├── underwriting.py        # Core underwriting entity and status tracking
│   ├── document.py            # Document metadata, storage paths, processing status
│   ├── processor.py           # Processor definitions, configurations, execution tracking
│   └── audit.py               # Audit trail for compliance and change tracking
├── schemas/                    # Pydantic schemas for API request/response validation
│   ├── __init__.py            # Schema base classes and common validators
│   ├── base.py                # Base response models, pagination, error formats
│   ├── underwriting.py        # Underwriting API schemas (create, update, list)
│   ├── document.py            # Document upload, metadata, and processing schemas
│   └── common.py              # Shared schemas (status enums, common fields)
├── database/                   # Database connection and data access layer
│   ├── __init__.py            # Database setup and session management exports
│   ├── connection.py          # Database URL construction, connection pooling
│   ├── session.py             # SQLAlchemy session factory and transaction management
│   └── repositories/          # Data access objects with business logic
│       ├── __init__.py        # Repository pattern base classes
│       ├── base_repository.py # Generic CRUD operations and query builders
│       ├── underwriting_repository.py # Underwriting-specific queries and operations
│       └── document_repository.py     # Document storage, retrieval, and metadata ops
├── events/                     # Event-driven architecture infrastructure
│   ├── __init__.py            # Event system exports and registration
│   ├── base.py                # Base event classes, event metadata, timestamps
│   ├── bus.py                 # In-memory event bus for synchronous processing
│   ├── handlers.py            # Event handler registration and dispatch logic
│   └── publisher.py           # Pub/Sub publisher for asynchronous events
├── utils/                      # Common utilities used across all modules
│   ├── __init__.py            # Utility function exports
│   ├── crypto.py              # Encryption, hashing, secure token generation
│   ├── validators.py          # Data validation helpers (email, phone, business rules)
│   ├── formatters.py          # Data formatting (currency, dates, phone numbers)
│   └── decorators.py          # Common decorators (retry logic, caching, timing)
├── exceptions/                 # Custom exception hierarchy for error handling
│   ├── __init__.py            # Exception exports and error hierarchy
│   ├── base.py                # Base exception classes with error codes
│   ├── business.py            # Business logic exceptions (validation, rules)
│   └── technical.py           # Technical exceptions (API failures, timeouts)
├── auth/                       # Authentication and authorization system
│   ├── __init__.py            # Auth system exports and middleware
│   ├── jwt.py                 # JWT token creation, validation, and refresh logic
│   ├── permissions.py         # Role-based access control (RBAC) and permissions
│   └── middleware.py          # Auth middleware for request authentication
├── monitoring/                 # Observability, metrics, and system health
│   ├── __init__.py            # Monitoring exports and setup
│   ├── metrics.py             # Custom metrics collection (Prometheus format)
│   ├── logging.py             # Structured logging with correlation IDs
│   └── tracing.py             # Distributed tracing for request flow analysis
└── constants/                  # System-wide constants and enumerations
    ├── __init__.py            # Constants exports and collections
    ├── status.py              # Underwriting status enums and transitions
    ├── events.py              # Event type constants and schemas
    └── processors.py          # Processor type definitions and configurations
```

## Team Module Structures

### Data Infrastructure Module (`src/aura/data_infrastructure/`) - Team 1
```
data_infrastructure/
├── __init__.py                 # Module exports and team-specific configurations
├── api/                        # REST API endpoints for data infrastructure operations
│   ├── __init__.py            # API router registration and common dependencies
│   ├── router.py              # Main router aggregating all endpoint modules
│   └── endpoints/             # Individual endpoint implementations
│       ├── storage.py         # File upload, download, metadata management APIs
│       ├── warehouse.py       # BigQuery data access, ETL status, analytics queries
│       └── health.py          # Data infrastructure health checks and status
├── services/                   # Business logic services for data operations
│   ├── __init__.py            # Service layer exports and dependency injection
│   ├── storage_service.py     # Cloud Storage operations (upload, lifecycle, metadata)
│   ├── warehouse_service.py   # BigQuery operations (ETL, queries, table management)
│   ├── etl_service.py         # Data transformation pipelines and job orchestration
│   └── cache_service.py       # Redis caching logic, cache invalidation strategies
├── repositories/               # Data access layer for external storage systems
│   ├── __init__.py            # Repository pattern implementations for data stores
│   ├── bigquery_repository.py # BigQuery client wrapper, query builders, result processing
│   ├── storage_repository.py  # Google Cloud Storage operations and file management
│   └── cache_repository.py    # Redis operations, cache key management, TTL handling
├── models/                     # Module-specific data models (not shared)
│   ├── __init__.py            # Local model definitions and relationships
│   ├── warehouse.py           # BigQuery table schemas and dimension/fact models
│   └── storage.py             # File metadata models and storage tracking
├── schemas/                    # API request/response schemas specific to data operations
│   ├── __init__.py            # Data infrastructure API schemas
│   ├── storage.py             # File upload requests, metadata responses, storage schemas
│   └── warehouse.py           # Analytics query requests, ETL job schemas, result formats
├── tasks/                      # Background tasks and job definitions
│   ├── __init__.py            # Celery/background task setup and routing
│   ├── etl_tasks.py           # ETL pipeline tasks, data transformation jobs
│   └── cleanup_tasks.py       # Storage lifecycle management, archival, cleanup jobs
├── config/                     # Module-specific configuration
│   ├── __init__.py            # Configuration exports and validation
│   ├── storage.py             # Cloud Storage settings, bucket configs, lifecycle rules
│   └── bigquery.py            # BigQuery project settings, dataset configs, table schemas
└── utils/                      # Module-specific utilities
    ├── __init__.py            # Utility function exports
    ├── file_utils.py          # File processing, validation, metadata extraction
    └── query_builder.py       # Dynamic SQL generation, query optimization helpers
```

### Data Collection Module (`src/aura/data_collection/`) - Team 2
```
data_collection/
├── __init__.py                 # Module initialization and team configuration
├── api/                        # User-facing APIs for data collection
│   ├── __init__.py            # API setup and common request handlers
│   ├── router.py              # Main router for all data collection endpoints
│   └── endpoints/             # Endpoint implementations for different operations
│       ├── documents.py       # Document CRUD, upload status, metadata management
│       ├── forms.py           # Dynamic form generation, submission, validation
│       ├── underwritings.py   # Underwriting lifecycle, status updates, user operations
│       └── uploads.py         # File upload handling, progress tracking, validation
├── services/                   # Business logic for data collection operations
│   ├── __init__.py            # Service layer organization and exports
│   ├── document_service.py    # Document processing, categorization, lifecycle management
│   ├── form_service.py        # Form generation, validation, submission processing
│   ├── upload_service.py      # File upload orchestration, chunking, progress tracking
│   ├── ocr_service.py         # Document AI integration, text extraction, processing
│   └── validation_service.py  # Data validation, business rules, quality checks
├── models/                     # Data models specific to collection operations
│   ├── __init__.py            # Local model definitions
│   ├── document.py            # Document metadata, processing status, relationships
│   ├── form.py                # Form configurations, field definitions, validation rules
│   └── upload.py              # Upload session tracking, chunk management, progress
├── schemas/                    # API schemas for data collection endpoints
│   ├── __init__.py            # Schema definitions and validation logic
│   ├── document.py            # Document API schemas (upload, update, metadata)
│   ├── form.py                # Form generation and submission schemas
│   └── upload.py              # File upload schemas, progress tracking, error handling
├── tasks/                      # Background processing tasks
│   ├── __init__.py            # Task definitions and job routing
│   ├── ocr_tasks.py           # Asynchronous OCR processing, text extraction
│   ├── validation_tasks.py    # Document validation, quality checks, categorization
│   └── categorization_tasks.py # AI-powered document type detection, metadata enrichment
├── event_handlers/             # Event processing for cross-module communication
│   ├── __init__.py            # Event handler registration and dispatch
│   └── document_handlers.py   # Document lifecycle event processing, status updates
├── utils/                      # Collection-specific utilities
│   ├── __init__.py            # Utility exports
│   ├── file_validators.py     # File type validation, security scanning, size checks
│   ├── form_builder.py        # Dynamic form generation, field rendering, validation
│   └── ocr_utils.py           # OCR result processing, confidence scoring, text cleanup
└── config/                     # Module configuration settings
    ├── __init__.py            # Configuration management
    ├── upload.py              # Upload limits, allowed file types, storage settings
    └── ocr.py                 # Document AI configuration, processing parameters
```

### Processing Engine Module (`src/aura/processing_engine/`) - Team 3
```
processing_engine/
├── __init__.py                 # Module setup and processor registry initialization
├── api/                        # APIs for processor management and monitoring
│   ├── __init__.py            # API router setup and authentication
│   ├── router.py              # Main routing for processor operations
│   └── endpoints/             # Endpoint implementations
│       ├── processors.py      # Processor CRUD, configuration, subscription management
│       ├── executions.py      # Execution tracking, status monitoring, retry operations
│       └── factors.py         # Factor extraction results, data retrieval, analytics
├── services/                   # Core processing business logic
│   ├── __init__.py            # Service layer coordination and exports
│   ├── orchestrator_service.py # Processor execution coordination, parallel processing
│   ├── processor_registry.py  # Dynamic processor registration, configuration management
│   ├── factor_service.py      # Factor calculation, validation, storage coordination
│   └── external_api_service.py # External API coordination, rate limiting, caching
├── processors/                 # Individual processor implementations (Team 3's main work)
│   ├── __init__.py            # Processor base classes and registration system
│   ├── base_processor.py      # Abstract base class defining processor interface
│   ├── bank_statements/       # Bank statement analysis processor
│   │   ├── __init__.py        # Bank statement processor module setup
│   │   ├── processor.py       # Main processor implementation and orchestration
│   │   ├── analyzer.py        # Revenue analysis, NSF detection, cash flow patterns
│   │   └── extractor.py       # Data extraction from PDFs, transaction categorization
│   ├── credit_bureaus/        # Credit bureau integration processors
│   │   ├── __init__.py        # Credit bureau processor coordination
│   │   ├── experian/          # Experian-specific processors
│   │   │   ├── business_processor.py # Business credit reports, trade lines, scores
│   │   │   └── owner_processor.py    # Owner background, personal credit analysis
│   │   └── equifax/           # Equifax-specific processors
│   │       ├── business_processor.py # Business credit history, payment patterns
│   │       └── principal_processor.py # Principal identity, credit verification
│   ├── identity/              # Identity verification processors
│   │   ├── __init__.py        # Identity processing coordination
│   │   ├── drivers_license_processor.py # License validation, identity verification
│   │   └── business_registration_processor.py # Business entity verification, EIN validation
│   ├── external_reports/      # Third-party report processors
│   │   ├── __init__.py        # External report processing setup
│   │   ├── clear_processor.py # Thomson Reuters CLEAR reports processing
│   │   └── data_merch_processor.py # Data Merch default reporting integration
│   └── documents/             # Document analysis processors
│       ├── __init__.py        # Document processing coordination
│       ├── contract_processor.py # Contract analysis, party verification, terms extraction
│       └── check_processor.py     # Voided check processing, account verification
├── external_integrations/      # External API client implementations
│   ├── __init__.py            # API client coordination and factory patterns
│   ├── base_client.py         # Abstract API client with retry, rate limiting, error handling
│   ├── clear_client.py        # Thomson Reuters CLEAR API client implementation
│   ├── experian_client.py     # Experian API client, authentication, request formatting
│   ├── equifax_client.py      # Equifax API integration, response parsing
│   └── state_registry_client.py # Secretary of State API clients for business verification
├── models/                     # Processing-specific data models
│   ├── __init__.py            # Model definitions for processing domain
│   ├── processor.py           # Processor configuration, execution tracking models
│   ├── execution.py           # Execution history, status tracking, error logging
│   └── factor.py              # Factor definitions, calculation results, validation
├── schemas/                    # API schemas for processing operations
│   ├── __init__.py            # Schema definitions for processing APIs
│   ├── processor.py           # Processor configuration and management schemas
│   ├── execution.py           # Execution status, progress tracking schemas
│   └── factor.py              # Factor extraction, validation, result schemas
├── tasks/                      # Background processing tasks
│   ├── __init__.py            # Task queue setup and job routing
│   ├── execution_tasks.py     # Processor execution jobs, parallel processing coordination
│   └── retry_tasks.py         # Failed execution retry logic, exponential backoff
├── event_handlers/             # Cross-module event processing
│   ├── __init__.py            # Event handler registration for processing events
│   └── processing_handlers.py # Document updates, re-processing triggers, status updates
├── utils/                      # Processing-specific utilities
│   ├── __init__.py            # Utility function exports
│   ├── factor_calculator.py   # Mathematical calculations, ratio analysis, scoring
│   ├── data_extractor.py      # Text extraction, pattern matching, data normalization
│   └── api_utils.py           # API request/response handling, authentication helpers
└── config/                     # Processing configuration management
    ├── __init__.py            # Configuration coordination and validation
    ├── processors.py          # Processor-specific settings, timeouts, resource limits
    └── external_apis.py       # API endpoints, credentials, rate limiting configurations
```

### AI Decision Module (`src/aura/ai_decision/`) - Team 4
```
ai_decision/
├── __init__.py                 # AI module setup and model initialization
├── api/                        # APIs for AI decision services
│   ├── __init__.py            # API setup with AI-specific authentication and rate limiting
│   ├── router.py              # Main routing for AI decision endpoints
│   └── endpoints/             # AI service endpoints
│       ├── suggestions.py     # AI suggestion generation, confidence scoring, explanations
│       ├── analytics.py       # Model performance analytics, A/B testing results
│       └── models.py          # Model management, versioning, deployment status
├── services/                   # AI business logic services
│   ├── __init__.py            # AI service coordination and model management
│   ├── decision_service.py    # Main decision orchestration, strategy selection
│   ├── rag_service.py         # Retrieval-Augmented Generation implementation
│   ├── vector_service.py      # Vector database operations, similarity search
│   ├── llm_service.py         # Large Language Model integration and prompt management
│   └── learning_service.py    # Continuous learning, feedback processing, model updates
├── models/                     # AI-specific data models
│   ├── __init__.py            # AI domain model definitions
│   ├── decision.py            # Decision tracking, confidence scoring, explanation storage
│   ├── suggestion.py          # Suggestion generation, ranking, A/B testing variants
│   └── performance.py         # Model performance metrics, accuracy tracking, drift detection
├── schemas/                    # AI API request/response schemas
│   ├── __init__.py            # AI-specific schema definitions and validation
│   ├── decision.py            # Decision generation requests, suggestion response formats
│   ├── suggestion.py          # Suggestion API schemas, confidence scores, explanations
│   └── analytics.py           # Analytics requests, performance metrics, model insights
├── ml/                         # Machine learning implementation components (Team 4's core work)
│   ├── __init__.py            # ML pipeline setup and model registry
│   ├── embeddings/            # Feature embedding and vectorization
│   │   ├── __init__.py        # Embedding pipeline setup
│   │   ├── feature_encoder.py # Convert underwriting factors to vector embeddings
│   │   └── vector_generator.py # Generate and manage vector representations
│   ├── rag/                   # Retrieval-Augmented Generation implementation
│   │   ├── __init__.py        # RAG pipeline coordination
│   │   ├── retriever.py       # Similar case retrieval from vector database
│   │   ├── context_builder.py # Context assembly for LLM prompts from retrieved cases
│   │   └── similarity_search.py # Advanced similarity algorithms and ranking
│   ├── llm/                   # Large Language Model integration
│   │   ├── __init__.py        # LLM client setup and model management
│   │   ├── prompt_manager.py  # Prompt template management, versioning, optimization
│   │   ├── response_parser.py # LLM response parsing, validation, error handling
│   │   └── client.py          # Vertex AI LLM client, request handling, retry logic
│   └── evaluation/            # Model performance and evaluation
│       ├── __init__.py        # Evaluation pipeline setup
│       ├── performance_tracker.py # Accuracy metrics, suggestion quality measurement
│       └── ab_testing.py      # A/B testing framework, statistical analysis
├── tasks/                      # Background AI processing tasks
│   ├── __init__.py            # AI task queue setup and job management
│   ├── suggestion_tasks.py    # Asynchronous suggestion generation, batch processing
│   ├── learning_tasks.py      # Model training, feedback processing, performance analysis
│   └── model_update_tasks.py  # Model deployment, vector database updates, cache refresh
├── event_handlers/             # AI event processing for cross-module communication
│   ├── __init__.py            # AI event handler registration
│   └── decision_handlers.py   # Decision completion events, learning triggers, performance tracking
├── utils/                      # AI-specific utilities and helpers
│   ├── __init__.py            # AI utility function exports
│   ├── prompt_utils.py        # Prompt construction, token management, template helpers
│   ├── vector_utils.py        # Vector operations, similarity calculations, normalization
│   └── evaluation_utils.py    # Performance calculation, statistical analysis, metrics
└── config/                     # AI system configuration
    ├── __init__.py            # AI configuration management and validation
    ├── ml.py                  # Machine learning model settings, hyperparameters
    ├── llm.py                 # LLM configuration, API settings, prompt templates
    └── vector_db.py           # Vector database configuration, indexing parameters
```

### Business Rules Module (`src/aura/business_rules/`) - Team 5
```
business_rules/
├── __init__.py                 # Business rules module setup and rule engine initialization
├── api/                        # APIs for rule management and validation
│   ├── __init__.py            # Rules API setup and admin authentication
│   ├── router.py              # Main routing for rules management endpoints
│   └── endpoints/             # Rule system endpoints
│       ├── rules.py           # Rule CRUD operations, testing, deployment
│       ├── validation.py      # Validation endpoint, pre-check execution, results
│       └── thresholds.py      # Threshold management, performance monitoring, adjustments
├── services/                   # Business logic services for rules
│   ├── __init__.py            # Rules service coordination and execution
│   ├── rules_engine.py        # Core rules engine, evaluation logic, result aggregation
│   ├── validation_service.py  # Multi-stage validation orchestration and reporting
│   ├── threshold_service.py   # Dynamic threshold management and optimization
│   └── compliance_service.py  # Regulatory compliance checking and reporting
├── rules/                      # Rule implementations (Team 5's main work)
│   ├── __init__.py            # Rule system setup and base classes
│   ├── base_rule.py           # Abstract rule class defining interface and common logic
│   ├── location_rules.py      # Geographic restrictions, state-specific requirements
│   ├── financial_rules.py     # Revenue requirements, time in business, financial ratios
│   ├── credit_rules.py        # Credit score thresholds, payment history requirements
│   └── compliance_rules.py    # Regulatory compliance, industry restrictions, KYC
├── validators/                 # Validation logic implementations
│   ├── __init__.py            # Validator system setup and registration
│   ├── base_validator.py      # Abstract validator class with common validation patterns
│   ├── precheck_validator.py  # Pre-check validation orchestration and early rejection
│   └── factor_validator.py    # Factor completeness, quality, and consistency validation
├── models/                     # Business rules data models
│   ├── __init__.py            # Rules domain model definitions
│   ├── rule.py                # Rule definitions, configurations, execution history
│   ├── validation.py          # Validation results, error tracking, reporting
│   └── threshold.py           # Threshold configurations, performance tracking, adjustments
├── schemas/                    # Rules API schemas
│   ├── __init__.py            # Rules API schema definitions
│   ├── rule.py                # Rule creation, modification, testing schemas
│   ├── validation.py          # Validation request and result schemas
│   └── threshold.py           # Threshold management and monitoring schemas
├── tasks/                      # Background rules processing
│   ├── __init__.py            # Rules task setup and job scheduling
│   └── validation_tasks.py    # Asynchronous validation, batch rule execution, reporting
├── event_handlers/             # Rules event processing
│   ├── __init__.py            # Rules event handler setup
│   └── validation_handlers.py # Processing completion events, validation triggers, result handling
├── utils/                      # Rules-specific utilities
│   ├── __init__.py            # Rules utility exports
│   ├── rule_parser.py         # Rule expression parsing, syntax validation, compilation
│   ├── json_logic.py          # JSON Logic implementation for dynamic rule evaluation
│   └── threshold_calculator.py # Threshold optimization, performance analysis, recommendations
└── config/                     # Rules system configuration
    ├── __init__.py            # Rules configuration management
    ├── rules.py               # Default rules, validation settings, compliance requirements
    └── thresholds.py          # Default thresholds, performance targets, adjustment parameters
```

### Workflow Orchestration Module (`src/aura/workflow_orchestration/`) - Team 6 (The System Coordinator)
```
workflow_orchestration/
├── __init__.py                 # Orchestration system initialization and event bus setup
├── api/                        # APIs for workflow monitoring and management
│   ├── __init__.py            # Workflow API setup and administrative access
│   ├── router.py              # Main routing for workflow management endpoints
│   └── endpoints/             # Workflow system endpoints
│       ├── workflows.py       # Workflow status monitoring, manual interventions, analytics
│       ├── events.py          # Event system monitoring, message tracking, debugging
│       └── monitoring.py      # System health dashboards, performance metrics, alerts
├── services/                   # Orchestration business logic (Team 6's core responsibility)
│   ├── __init__.py            # Orchestration service coordination and exports
│   ├── orchestrator_service.py # Main workflow coordination, cross-team communication
│   ├── event_service.py       # Event routing, filtering, transformation, delivery
│   ├── workflow_service.py    # Workflow lifecycle management, state transitions
│   └── monitoring_service.py  # System observability, metrics collection, alerting
├── workflows/                  # Workflow implementations (Team 6's main work)
│   ├── __init__.py            # Workflow system setup and base classes
│   ├── base_workflow.py       # Abstract workflow class with common orchestration patterns
│   ├── underwriting_workflow.py # Main underwriting process orchestration and coordination
│   └── retry_workflow.py      # Error recovery workflows, compensation logic, rollback
├── events/                     # Event system implementation (Team 6's core infrastructure)
│   ├── __init__.py            # Event system initialization and configuration
│   ├── event_bus.py           # In-memory event bus for synchronous cross-module communication
│   ├── publishers/            # Event publishing implementations
│   │   ├── __init__.py        # Publisher setup and routing logic
│   │   ├── pubsub_publisher.py # Google Cloud Pub/Sub integration for async events
│   │   └── memory_publisher.py # In-memory publisher for immediate synchronous events
│   └── handlers/              # Event handler implementations
│       ├── __init__.py        # Handler registration and dispatch logic
│       ├── workflow_handlers.py # Workflow progression events, status updates, transitions
│       ├── monitoring_handlers.py # System health events, metrics collection, alerting
│       └── error_handlers.py   # Error event processing, retry coordination, dead letters
├── state_machine/              # State management implementation (Team 6's workflow engine)
│   ├── __init__.py            # State machine setup and configuration
│   ├── state_manager.py       # State persistence, transitions, concurrency control
│   ├── transitions.py         # Valid state transition definitions and validation logic
│   └── validators.py          # State change validation, business rule enforcement
├── models/                     # Workflow-specific data models
│   ├── __init__.py            # Workflow domain model definitions
│   ├── workflow.py            # Workflow execution tracking, progress monitoring
│   ├── event.py               # Event metadata, correlation IDs, processing history
│   └── state.py               # State definitions, transition history, audit trails
├── schemas/                    # Workflow API schemas
│   ├── __init__.py            # Workflow API schema definitions
│   ├── workflow.py            # Workflow monitoring and management schemas
│   ├── event.py               # Event tracking and debugging schemas
│   └── monitoring.py          # System health and performance monitoring schemas
├── tasks/                      # Background orchestration tasks
│   ├── __init__.py            # Orchestration task setup and scheduling
│   ├── workflow_tasks.py      # Workflow progression tasks, timeout handling, recovery
│   ├── cleanup_tasks.py       # System cleanup, log rotation, performance optimization
│   └── monitoring_tasks.py    # Health checks, metric collection, alert processing
├── utils/                      # Orchestration-specific utilities
│   ├── __init__.py            # Orchestration utility exports
│   ├── workflow_utils.py      # Workflow coordination helpers, state management utilities
│   ├── event_utils.py         # Event processing utilities, correlation ID management
│   └── state_utils.py         # State transition helpers, validation utilities
└── config/                     # Orchestration system configuration
    ├── __init__.py            # Orchestration configuration management
    ├── workflows.py           # Workflow definitions, timeout settings, retry policies
    ├── events.py              # Event system configuration, routing rules, delivery settings
    └── monitoring.py          # Monitoring thresholds, alert configurations, dashboard settings
```

### Configuration Structure (`config/`) - Environment and System Configuration
```
config/
├── settings.py             # Main application settings aggregator and dependency injection setup
├── database.py             # Database connection pooling, URL construction, migration settings
├── logging.py              # Centralized logging configuration, formatters, handlers, correlation IDs
├── redis.py               # Redis connection settings, cache configurations, session management
├── gcp.py                 # Google Cloud Platform service configurations and authentication
├── security.py            # Security settings, JWT configuration, CORS policies, rate limiting
└── environments/          # Environment-specific configuration overrides
    ├── __init__.py        # Environment detection and configuration loading logic
    ├── base.py            # Base configuration class with default values and validation
    ├── development.py     # Development environment (debug mode, local services, relaxed security)
    ├── staging.py         # Staging environment (production-like setup with test data access)
    ├── production.py      # Production environment (optimized performance, security hardened)
    └── testing.py         # Test environment (in-memory databases, mocked external services)
```

### Testing Structure (`tests/`) - Comprehensive Test Coverage
```
tests/
├── conftest.py            # Pytest configuration, shared fixtures, test database setup, mocking
├── fixtures/              # Test data fixtures and factory methods
│   ├── __init__.py        # Fixture exports and factory registration
│   ├── underwritings.py   # Sample underwriting data, status progressions, edge cases
│   ├── documents.py       # Test documents, file uploads, OCR results, validation scenarios
│   └── processors.py      # Processor execution results, factor data, API responses
├── unit/                  # Fast, isolated unit tests (no external dependencies)
│   ├── __init__.py        # Unit test configuration and utilities
│   ├── shared/            # Tests for shared infrastructure components
│   │   ├── test_models.py        # Database model validation, relationships, constraints
│   │   ├── test_repositories.py  # Repository pattern tests, query logic, data access
│   │   ├── test_events.py        # Event system tests, publishing, handling, ordering
│   │   └── test_utils.py         # Utility function tests, formatters, validators
│   ├── data_infrastructure/      # Team 1 unit tests
│   │   ├── test_storage_service.py    # File upload, metadata extraction, lifecycle
│   │   ├── test_warehouse_service.py  # BigQuery operations, ETL logic, queries
│   │   └── test_cache_service.py      # Redis operations, invalidation, TTL handling
│   ├── data_collection/          # Team 2 unit tests
│   │   ├── test_document_service.py   # Document processing, validation, categorization
│   │   ├── test_form_service.py       # Form generation, validation, submission
│   │   └── test_ocr_service.py        # OCR processing, text extraction, quality
│   ├── processing_engine/        # Team 3 unit tests
│   │   ├── test_orchestrator.py       # Processor coordination, parallel execution
│   │   ├── test_processors/           # Individual processor tests
│   │   │   ├── test_bank_statements.py    # Bank statement analysis logic
│   │   │   ├── test_credit_bureaus.py     # Credit report processing
│   │   │   └── test_identity.py           # Identity verification logic
│   │   └── test_external_clients.py      # API client functionality, error handling
│   ├── ai_decision/              # Team 4 unit tests
│   │   ├── test_rag_service.py        # RAG implementation, similarity search
│   │   ├── test_llm_service.py        # LLM integration, prompt management
│   │   ├── test_vector_service.py     # Vector operations, embedding generation
│   │   └── test_learning_service.py   # Learning pipeline, performance tracking
│   ├── business_rules/           # Team 5 unit tests
│   │   ├── test_rules_engine.py       # Rule evaluation, logic processing
│   │   ├── test_validators.py         # Validation logic, pre-check criteria
│   │   └── test_rule_types.py         # Individual rule implementations
│   └── workflow_orchestration/   # Team 6 unit tests
│       ├── test_orchestrator.py       # Workflow coordination, state management
│       ├── test_event_bus.py          # Event publishing, handling, ordering
│       ├── test_state_machine.py      # State transitions, validation, consistency
│       └── test_monitoring.py         # Health monitoring, metrics, alerting
├── integration/           # Integration tests for component interactions
│   ├── __init__.py        # Integration test setup and database management
│   ├── api/               # API integration tests (full request/response cycles)
│   │   ├── test_underwriting_api.py   # End-to-end underwriting API flows
│   │   ├── test_document_api.py       # Document upload and processing APIs
│   │   └── test_processor_api.py      # Processor management and execution APIs
│   ├── database/          # Database integration tests
│   │   ├── test_migrations.py         # Schema migration validation
│   │   ├── test_repositories.py       # Repository integration with actual database
│   │   └── test_transactions.py       # Transaction management and rollback testing
│   ├── external_apis/     # External service integration tests
│   │   ├── test_clear_integration.py  # Thomson Reuters CLEAR API integration
│   │   ├── test_credit_bureaus.py     # Experian/Equifax integration testing
│   │   └── test_ocr_integration.py    # Document AI OCR integration
│   └── workflows/         # Cross-module workflow integration tests
│       ├── test_processing_flow.py    # Document to factor extraction flow
│       ├── test_decision_flow.py      # Processing to AI decision flow
│       └── test_error_recovery.py     # Error handling and retry workflows
└── e2e/                   # End-to-end tests simulating complete user journeys
    ├── __init__.py        # E2E test configuration and browser automation setup
    ├── test_underwriting_flow.py     # Complete underwriting process from submission to decision
    ├── test_processing_flow.py       # Document upload through all processors to factors
    ├── test_decision_flow.py         # AI suggestion generation and human decision process
    └── test_error_scenarios.py       # Error handling, recovery, and edge case testing
```

### Documentation Structure (`docs/`) - Comprehensive Project Documentation
```
docs/
├── README.md              # Project overview, quick start guide, contribution guidelines
├── CONTRIBUTING.md        # Development guidelines, code standards, PR process, testing
├── DEPLOYMENT.md          # Infrastructure setup, deployment procedures, environment config
├── api/                   # API documentation and specifications
│   ├── openapi.json       # Generated OpenAPI specification for all endpoints
│   ├── endpoints/         # Individual endpoint documentation with examples
│   │   ├── underwritings.md    # Underwriting API documentation and usage examples
│   │   ├── documents.md        # Document management API documentation
│   │   ├── processors.md       # Processor management and execution APIs
│   │   └── decisions.md        # AI decision and suggestion APIs
│   └── schemas/           # Data model documentation and relationship diagrams
│       ├── database.md         # Database schema documentation and ERD
│       ├── events.md           # Event schema documentation and flow diagrams
│       └── api_models.md       # API request/response model documentation
├── architecture/          # System architecture and design documentation
│   ├── overview.md        # High-level system architecture and design principles
│   ├── data_flow.md       # Data flow diagrams and processing pipelines
│   ├── event_system.md    # Event-driven architecture documentation
│   ├── modules.md         # Module responsibilities and interaction patterns
│   └── deployment.md      # Infrastructure architecture and scaling strategies
├── development/           # Developer guides and best practices
│   ├── setup.md           # Local development environment setup and configuration
│   ├── coding_standards.md # Code style, naming conventions, best practices
│   ├── testing.md         # Testing strategies, fixture usage, coverage requirements
│   ├── debugging.md       # Debugging techniques, logging, troubleshooting
│   └── team_guides/       # Team-specific development guides
│       ├── team1_data_infrastructure.md # Team 1 development patterns and practices
│       ├── team2_data_collection.md     # Team 2 API development guidelines
│       ├── team3_processing_engine.md   # Team 3 processor development guide
│       ├── team4_ai_decision.md         # Team 4 ML development practices
│       ├── team5_business_rules.md      # Team 5 rules development guidelines
│       └── team6_workflow_orchestration.md # Team 6 orchestration patterns
└── operations/            # Operational guides and procedures
    ├── monitoring.md      # System monitoring, metrics, dashboard configuration
    ├── troubleshooting.md # Common issues, debugging procedures, error resolution
    ├── scaling.md         # Performance optimization, scaling strategies, capacity planning
    ├── maintenance.md     # Routine maintenance, updates, backup procedures
    └── security.md        # Security procedures, access control, compliance requirements
```

## Key Architectural Benefits of This Structure:

### **Module Isolation with Shared Foundation:**
- Each team module is self-contained with its own API, services, and models
- Shared infrastructure prevents duplication
- Clear boundaries enable parallel development

### **Layered Architecture:**
- **API Layer**: REST endpoints and request/response handling
- **Service Layer**: Business logic and orchestration
- **Repository Layer**: Data access abstraction
- **Model Layer**: Database and domain models

### **Event-Driven Integration:**
- Shared event system enables loose coupling
- Each module has event handlers for cross-module communication
- Centralized event bus in workflow orchestration

### **Configuration Management:**
- Environment-specific configurations
- Module-specific config files
- Centralized settings management

### **Testing Strategy:**
- Comprehensive test coverage at all levels
- Module-specific test isolation
- End-to-end workflow testing

This structure supports the monolith approach while maintaining clear module boundaries, enabling teams to work independently while sharing common infrastructure and ensuring system cohesion.
