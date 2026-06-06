# University AI Chatbot Platform

A production-ready AI chatbot for government university websites. Built with **FastAPI**, **PostgreSQL**, **ChromaDB**, and **Gemini 2.5 Flash**.

## Features

- **9-Stage Chat Pipeline**: Greeting → FAQ → Normalize → Cache → Scope → RAG → Gemini → Save → Return
- **Cost Optimized**: Greetings, FAQs, and cached answers never call the AI API
- **RAG Engine**: ChromaDB vector search with source citations
- **Admin Panel**: Dashboard analytics, document management, chat logs
- **Chat Widget**: Single `<script>` tag integration, desktop floating + mobile fullscreen
- **50+ Concurrent Users**: Async PostgreSQL + Uvicorn workers

## Quick Start

### Prerequisites
- Python 3.11+
- PostgreSQL 14+
- Docker & Docker Compose (for containerized deployment)

### Local Development

```bash
# 1. Install dependencies
cd backend
pip install -r requirements.txt

# 2. Configure environment
cp .env.example .env
# Edit .env — set your GEMINI_API_KEY

# 3. Start PostgreSQL (if not using Docker)
# Ensure PostgreSQL is running on localhost:5432

# 4. Run the server
python app.py
```

### Docker Deployment

```bash
# Set your Gemini API key
export GEMINI_API_KEY=your_key_here

# Deploy
cd deployment
bash deploy.sh
```

## Access Points

| Service | URL |
|---------|-----|
| API | http://localhost:8000 |
| API Docs | http://localhost:8000/docs |
| Widget Demo | http://localhost/widget/chatbot.html |
| Admin Panel | http://localhost/admin/dashboard.html |
| Health Check | http://localhost:8000/api/health |

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/chat` | Send a chat message |
| POST | `/api/upload` | Upload a document |
| GET | `/api/analytics` | Dashboard statistics |
| GET | `/api/logs` | Paginated chat logs |
| GET | `/api/documents` | List uploaded documents |
| DELETE | `/api/documents/{id}` | Delete a document |
| POST | `/api/rebuild-index` | Rebuild ChromaDB index |
| GET | `/api/health` | System health check |

## Widget Integration

Add one line to any university webpage:

```html
<script src="https://chat.university.edu/widget.js"></script>
```

## Project Structure

```
university-ai/
├── backend/
│   ├── api/          # FastAPI route handlers
│   ├── services/     # Business logic (greeting, FAQ, cache, RAG, Gemini, scope)
│   ├── database/     # SQLAlchemy models + async engine
│   ├── utils/        # PDF loader, chunker, validator, rate limiter, logger
│   ├── data/         # JSON config (greetings, stopwords, keywords)
│   ├── prompts/      # Gemini prompt template
│   ├── app.py        # FastAPI application entry point
│   └── config.py     # Pydantic settings
├── widget/           # Self-contained chat widget (JS + CSS)
├── admin-panel/      # Admin dashboard (HTML + CSS + JS)
├── uploads/          # Uploaded documents
├── chroma/           # ChromaDB vector storage
├── logs/             # Application logs
├── nginx/            # Reverse proxy config
└── deployment/       # Docker + deploy script
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `GEMINI_API_KEY` | (required) | Google Gemini API key |
| `GEMINI_MODEL` | gemini-2.5-flash | Gemini model name |
| `DATABASE_URL` | postgresql+asyncpg://... | PostgreSQL connection |
| `RATE_LIMIT_REQUESTS` | 100 | Max requests per IP per hour |
| `MAX_MESSAGE_LENGTH` | 500 | Max chat message characters |
| `LOG_LEVEL` | INFO | Logging level |

## License

MIT
