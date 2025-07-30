# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## AI Usage Notes
When assisting with tasks in this repo:
- Prioritize readability, modularity, and low-latency performance
- Follow the service boundaries defined in `services/`
- Avoid external APIs unless explicitly whitelisted (e.g. Airtable)
- Use `OLLAMA_MODEL` from env for LLM inference

## Project Overview
baseCamp is an AI-powered intake and CRM enrichment service designed for small businesses (mechanics, med spas, consultants). The system captures client inquiries through embeddable forms or messages, uses a local LLM (via Ollama) to analyze intent and urgency, and stores the enriched lead data in Airtable for follow-up.

## System Flow
1. **User Input** → Text from form/chat
2. **LLM Enrichment** → Classify intent, extract entities, score lead quality
3. **Embedding + ChromaDB** → Store/query semantically similar leads to avoid duplicates
4. **Airtable Sync** → Push structured lead into Airtable CRM

## Tech Stack
- **Backend**: FastAPI + Pydantic for API and validation
- **LLM**: Ollama (running Mistral or Claude-style models)
- **Vector DB**: ChromaDB for local embeddings
- **CRM**: Airtable with API integration
- **Automation** (optional): Zapier/n8n for notifications

## Project Structure

**Status**: ✅ Complete foundation structure

```
basecamp/
├── src/
│   ├── main.py                 # ✅ FastAPI application entry point
│   ├── models/                 # 🚧 Pydantic data models (to implement)
│   │   ├── __init__.py        # ✅ Package marker
│   │   ├── lead.py            # 📋 Lead data structures 
│   │   └── airtable.py        # 📋 Airtable record models
│   ├── services/              # 🚧 Business logic layer (to implement)
│   │   ├── __init__.py        # ✅ Package marker
│   │   ├── llm_service.py     # 📋 Ollama LLM integration
│   │   ├── vector_service.py  # 📋 ChromaDB operations
│   │   └── airtable_service.py # 📋 Airtable API client
│   ├── api/                   # 🚧 API route handlers (to implement)
│   │   ├── __init__.py        # ✅ Package marker
│   │   ├── intake.py          # 📋 Lead intake endpoints
│   │   └── leads.py           # 📋 Lead management endpoints
│   └── config/                # ✅ Configuration management
│       ├── __init__.py        # ✅ Package marker
│       └── settings.py        # ✅ Environment variables and settings
├── tests/                     # ✅ Test suite structure
│   └── __init__.py            # ✅ Package marker
├── docs/                      # ✅ Documentation directory
├── requirements.md            # ✅ System requirements documentation
├── todo.md                    # ✅ Development roadmap
├── tech-stack.md              # ✅ Technology documentation  
├── design-notes.md            # ✅ Architecture and design decisions
├── docker-compose.yml         # ✅ Container orchestration
├── Dockerfile                 # ✅ Container definition
├── pyproject.toml            # ✅ Project metadata and dependencies
├── requirements.txt          # ✅ Python dependencies
├── requirements-dev.txt      # ✅ Development dependencies
├── .env.example              # ✅ Environment variable template
├── .gitignore                # ✅ Git ignore patterns
├── .pre-commit-config.yaml   # ✅ Pre-commit hooks
└── .flake8                   # ✅ Linting configuration

Legend: ✅ Complete | 🚧 Structure ready | 📋 To implement
```

## Environment Variables
```bash
# LLM Configuration
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=mistral

# Vector Database
CHROMA_PERSIST_DIRECTORY=./chroma_db

# Airtable Integration
AIRTABLE_API_KEY=your_airtable_api_key
AIRTABLE_BASE_ID=your_base_id
AIRTABLE_TABLE_NAME=Leads

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
DEBUG=false
```

## Development Commands

**Status**: ✅ Foundation complete - ready for development

```bash
# Project setup
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows
pip install -r requirements-dev.txt

# Development server
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
# or
python -m src.main

# Testing (framework ready, tests to be implemented)
pytest tests/                    # Run all tests
pytest tests/test_services/      # Run service tests only
pytest -k "test_llm"            # Run specific test pattern
pytest --cov=src --cov-report=html  # Run with coverage

# Code quality
black src/ tests/               # Format code
flake8 src/ tests/              # Lint code
mypy src/                       # Type checking
pre-commit run --all-files      # Run all quality checks

# Docker operations
docker-compose up -d            # Start all services (Ollama + API)
docker-compose up ollama        # Start only Ollama service
docker-compose logs -f api      # Follow API logs
docker-compose down             # Stop all services
```

## Architecture & Data Flow

### Service-Oriented Architecture
The system follows a layered architecture with clear service boundaries:

1. **API Layer** (`src/api/`): FastAPI routers handling HTTP requests
2. **Service Layer** (`src/services/`): Business logic encapsulation
   - `LLMService`: Ollama integration for lead analysis
   - `VectorService`: ChromaDB for semantic similarity
   - `CRMService`: Airtable synchronization
3. **Data Layer**: ChromaDB (vectors) + Airtable (structured data)
4. **External Dependencies**: Ollama (local LLM), Airtable API

### Lead Processing Pipeline
```
Input → Validation → Raw Storage → Embedding Generation → 
Similarity Check → LLM Analysis → Lead Enrichment → CRM Sync → Response
```

Key processing decisions:
- **Async Processing**: Use FastAPI BackgroundTasks for non-blocking LLM operations
- **Graceful Degradation**: Continue processing even if LLM/vector services fail
- **Duplicate Detection**: Semantic similarity search before expensive LLM analysis
- **Error Handling**: Circuit breaker pattern for external service failures

### Data Models Hierarchy
- `LeadInput` (raw form data) → `EnrichedLead` (with AI analysis) → `AirtableRecord` (CRM format)
- Contact info validation with PII handling
- Configurable prompt templates per business type (automotive, medspa, consulting)

## API Design
RESTful endpoints following `/api/v1/` pattern:
- `POST /intake` - Main lead processing endpoint
- CRUD operations on `/leads/{id}`
- `/leads/{id}/similar` - Semantic similarity search
- `/health` - Service dependency health checks

## Configuration Management
- Pydantic BaseSettings for type-safe environment variable handling
- Service factory pattern for dependency injection
- Strategy pattern for business-type-specific prompt templates