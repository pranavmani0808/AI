# AI Search Engine - Phase 1

This repository contains the foundation setup (Phase 1) for the AI Search Engine. It includes a containerized development environment with a Next.js frontend, FastAPI backend, Celery worker, PostgreSQL, Redis, Qdrant vector database, and SearXNG metasearch engine.

## Architecture Diagram

```text
                  ┌─────────────┐
                  │   Next.js   │
                  │    :3000    │
                  └──────┬──────┘
                         │
                         ▼
                  ┌─────────────┐
                  │   FastAPI   │
                  │    :8000    │
                  └──────┬──────┘
                         │
        ┌────────────────┼────────────────┐
        │                │                │
        ▼                ▼                ▼
    SearXNG           Qdrant          PostgreSQL
     :8080             :6333            :5432
        │
        │
        └── Search Discovery

                         │
                         ▼
                       Redis
                       :6379
                         │
                         ▼
                  Celery Worker
```

## Folder Structure

```text
ai-search-engine/
├── backend/            # FastAPI Backend
│   ├── api/            # Placeholder API routers (search, crawl, chat)
│   ├── core/           # App Configuration (Pydantic Settings) & Celery initialization
│   ├── database/       # SQLAlchemy (Postgres) & Redis connection managers
│   ├── main.py         # App entrypoint with liveness/readiness endpoints
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/           # Next.js Frontend (TypeScript, Tailwind CSS)
│   ├── src/
│   ├── public/
│   ├── package.json
│   └── Dockerfile
├── searxng/
│   └── settings.yml    # SearXNG local configuration
├── .env                # Local Environment credentials (gitignored)
├── .env.example        # Environment template file
├── docker-compose.yml  # Docker orchestration config with service healthchecks
└── README.md           # Project documentation
```

## Quick Start

### 1. Configure the Environment
Copy the example environment variables and configure them:
```bash
cp .env.example .env
```
Ensure you update any default credentials (like the SearXNG secret key).

### 2. Start the Stack
Build and launch all services in detached mode:
```bash
docker compose up --build -d
```

### 3. Verify Status
Ensure all containers are healthy:
```bash
docker compose ps
```

## API Verification

- **FastAPI Documentation:** [http://localhost:8000/docs](http://localhost:8000/docs)
- **Backend Liveness Check:** `curl http://localhost:8000/health`
- **Backend Readiness Check (DBs + Search Engines):** `curl http://localhost:8000/health/ready`
- **SearXNG API:** `curl "http://localhost:8080/search?q=test&format=json"`
- **Qdrant Dashboard:** [http://localhost:6333/dashboard](http://localhost:6333/dashboard)
- **Next.js Frontend:** [http://localhost:3000](http://localhost:3000)
