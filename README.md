<pre>

oooo                                              oooooooo8                                      
 888ooooo     ooooooo    oooooooo8   ooooooooo8 o888     88   ooooooo   oo ooo oooo  ooooooooo   
 888    888   ooooo888  888ooooooo  888oooooo8  888           ooooo888   888 888 888  888    888 
 888    888 888    888          888 888         888o     oo 888    888   888 888 888  888    888 
o888ooo88    88ooo88 8o 88oooooo88    88oooo888  888oooo88   88ooo88 8o o888o888o888o 888ooo88   
                                                                                     o888        

# baseCamp

AI-powered intake and CRM enrichment service for small businesses. Automatically captures, analyzes, and organizes client inquiries using local LLM processing.

## Overview

baseCamp transforms raw client inquiries into structured, actionable leads by:
- Capturing form submissions and messages
- Using AI to classify intent and urgency
- Detecting duplicate leads through semantic similarity
- Syncing enriched data to Airtable CRM

Perfect for mechanics, med spas, consultants, and other service businesses looking to streamline their lead management.

## Features

- **AI-Powered Analysis**: Local LLM processing via Ollama for privacy and speed
- **Smart Deduplication**: Vector embeddings prevent duplicate lead processing
- **CRM Integration**: Seamless Airtable synchronization
- **Embeddable Forms**: Easy integration into existing websites
- **Lead Scoring**: Automatic urgency and quality assessment

## Quick Start

### Prerequisites

- Python 3.11+
- [Ollama](https://ollama.ai/) installed and running
- Airtable account and API key

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd baseCamp
```

2. Set up Python environment:
```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements-dev.txt
```

3. Configure environment:
```bash
cp .env.example .env
# Edit .env with your Airtable credentials
```

4. Start Ollama and pull a model:
```bash
ollama pull mistral
```

5. Run the development server:
```bash
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

Visit `http://localhost:8000/docs` for the interactive API documentation.

## Configuration

Key environment variables:

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
```

## API Usage

### Submit a Lead

```bash
curl -X POST "http://localhost:8000/api/v1/intake" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "John Doe",
    "email": "john@example.com",
    "phone": "+1234567890",
    "message": "My car is making strange noises when I brake",
    "business_type": "automotive"
  }'
```

### Health Check

```bash
curl http://localhost:8000/health
```

## Development

### Commands

```bash
# Run tests
pytest tests/

# Code formatting
black src/ tests/

# Linting
flake8 src/ tests/

# Type checking
mypy src/

# Run all quality checks
pre-commit run --all-files
```

### Docker

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f api

# Stop services
docker-compose down
```

## Architecture

- **API Layer**: FastAPI with async request handling
- **Service Layer**: Modular business logic (LLM, Vector, CRM services)
- **Data Layer**: ChromaDB for embeddings, Airtable for structured data
- **LLM**: Local Ollama instance for privacy and performance

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests and quality checks
5. Submit a pull request

## License

[Add your license here]

## Support

For questions or issues, please open a GitHub issue or contact [your-email@example.com].
</pre>
