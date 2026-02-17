# Interview Project: Scalable Web Services with FastAPI

A complete, production-oriented FastAPI project that demonstrates the technologies and practices from the job description: **scalable web services**, **RESTful APIs**, **PostgreSQL**, **Redis**, **Elasticsearch**, **queue systems (Celery + RabbitMQ)**, **Docker**, **TDD/BDD**, **SOLID design**, **CI/CD**, and **monitoring (Prometheus & Grafana)**.

---

## Table of Contents

- [Technologies Used](#technologies-used)
- [Project Structure](#project-structure)
- [Which Part Solves Which Challenge](#which-part-solves-which-challenge)
- [Design Rationale: Why This Is a Good Design](#design-rationale-why-this-is-a-good-design)
- [Quick Start](#quick-start)
- [API Overview](#api-overview)
- [Running Tests](#running-tests)
- [Monitoring](#monitoring)
- [CI/CD](#cicd)

---

## Technologies Used

| Requirement / Nice-to-Have | Technology | Where in the Project |
|----------------------------|------------|----------------------|
| **Programming language** | Python 3.12 | Entire app |
| **Web framework** | FastAPI | `app/main.py`, all `app/api/` |
| **RESTful APIs** | FastAPI (OpenAPI, validation) | `app/api/v1/endpoints/` |
| **OOP & SOLID** | Services, repositories, DI | `app/services/`, `app/db/repositories/`, `app/core/dependencies.py` |
| **PostgreSQL** | SQLAlchemy 2 (async) + asyncpg | `app/db/`, `alembic/` |
| **Redis** | redis (async) | `app/cache/redis_client.py` |
| **Elasticsearch** | elasticsearch (async) | `app/search/elasticsearch_client.py` |
| **Queue management** | Celery + RabbitMQ | `app/queue/celery_app.py`, `app/queue/tasks.py` |
| **Docker & docker-compose** | Dockerfile, docker-compose.yml | Root, all services |
| **TDD / BDD** | pytest, pytest-asyncio, pytest-bdd | `tests/` |
| **Git / version control** | Alembic migrations | `alembic/` |
| **CI/CD** | GitHub Actions | `.github/workflows/ci.yml` |
| **Microservices / event-driven** | Celery tasks, async indexing | `app/queue/tasks.py`, `app/services/item_service.py` |
| **Monitoring & observability** | Prometheus, Grafana | `app/main.py` (metrics), `monitoring/` |

---

## Project Structure

```
interviews/
├── app/
│   ├── main.py                 # FastAPI app, lifespan, Prometheus mount
│   ├── config.py               # Pydantic settings (env)
│   ├── api/v1/
│   │   ├── router.py           # Aggregates v1 endpoints
│   │   └── endpoints/
│   │       ├── health.py       # Liveness / readiness
│   │       ├── users.py        # Register, login (JWT)
│   │       ├── items.py        # CRUD items (REST)
│   │       └── search.py       # Elasticsearch search
│   ├── core/
│   │   ├── security.py         # Password hashing, JWT
│   │   └── dependencies.py     # Auth, DB session injection
│   ├── db/
│   │   ├── base.py             # SQLAlchemy Base
│   │   ├── session.py         # Async engine, get_db
│   │   ├── models/             # User, Item
│   │   └── repositories/       # Repository pattern (data access)
│   ├── schemas/                # Pydantic request/response
│   ├── services/               # Business logic (ItemService)
│   ├── cache/                  # Redis client, cache_get/set/delete
│   ├── search/                 # Elasticsearch client, index, search
│   └── queue/                  # Celery app, tasks (index_item_task)
├── alembic/                    # DB migrations
├── monitoring/
│   ├── prometheus.yml          # Scrape API /metrics
│   └── grafana/provisioning/   # Datasource (Prometheus)
├── tests/                      # Unit, API, BDD (pytest-bdd)
├── docker-compose.yml          # API, Celery, PostgreSQL, Redis, RabbitMQ, ES, Prometheus, Grafana
├── Dockerfile
├── requirements.txt
└── .github/workflows/ci.yml    # CI: test, lint
```

---

## Which Part Solves Which Challenge

These are typical interview challenges and where the project addresses them.

| Challenge | Solution in This Project |
|-----------|--------------------------|
| **Scalability** | Async I/O (FastAPI, asyncpg, Redis, ES), connection pooling in `app/db/session.py`, Celery for offloading work. |
| **Performance** | Redis caching in `app/cache/` and `ItemService.get_by_id`; eager loading in `ItemRepository.get_by_id_with_owner` and `get_many_with_owner` to avoid N+1 queries. |
| **Database query optimization** | Repositories centralize queries; `selectinload(Item.owner)` in `app/db/repositories/item_repository.py`; indexes on `email`, `owner_id`, `title` in migrations. |
| **RESTful API design** | Resource-based routes in `app/api/v1/endpoints/items.py` (GET/POST/PUT/DELETE), proper status codes (201, 404, 401), pagination via `skip`/`limit`. |
| **Reliable services** | Health endpoints in `health.py`; graceful degradation in Redis/ES (cache_get returns None on failure); Celery retries in `app/queue/tasks.py`. |
| **Best practices & architecture** | SOLID: repositories (Single Responsibility, Dependency Inversion), services orchestrate use cases; Pydantic for validation and config. |
| **Breaking down complex problems** | Item flow split into: API → Service → Repository/Cache/Queue; search indexing decoupled via Celery task. |
| **Queue management** | Celery + RabbitMQ in `app/queue/`; `index_item_task` for async Elasticsearch indexing (event-driven: API publishes, worker consumes). |
| **Caching** | Redis in `app/cache/redis_client.py`; cache invalidation on update/delete in `ItemService`. |
| **Search and analytics** | Elasticsearch in `app/search/elasticsearch_client.py`; index mapping, full-text search in `search_items`; search API in `endpoints/search.py`. |
| **Version control & schema changes** | Alembic in `alembic/`; migrations versioned and reversible. |
| **Docker** | Multi-service stack in `docker-compose.yml`; multi-stage Dockerfile; non-root user in Dockerfile. |
| **TDD / BDD** | pytest in `tests/test_health.py`, `tests/test_items_api.py`; pytest-bdd in `tests/features/` and `tests/step_defs/`. |
| **CI/CD** | GitHub Actions in `.github/workflows/ci.yml`: run tests and lint on push/PR. |
| **Event-driven / microservice-style** | Item create/update enqueues `index_item_task` instead of blocking on Elasticsearch; clear producer/consumer boundary. |
| **Monitoring & observability** | Prometheus metrics mounted at `/metrics` in `app/main.py`; Prometheus + Grafana in `docker-compose` and `monitoring/`. |

---

## Design Rationale: Why This Is a Good Design

1. **Layered architecture (API → Service → Repository)**  
   Controllers only handle HTTP; services contain business logic and orchestrate repositories, cache, and queue. This keeps responsibilities clear and makes testing and changes (e.g. new storage or queue) easier.

2. **Repository pattern**  
   All database access goes through repositories (`app/db/repositories/`). This centralizes query logic, avoids N+1 via eager loading, and allows swapping or mocking implementations for tests (Dependency Inversion).

3. **Dependency injection (FastAPI Depends)**  
   DB session, Redis, and auth are injected via `get_db`, `get_redis`, and `get_current_user_id`. The app does not create global connections inside request handlers, which improves testability and avoids connection leaks.

4. **Cache-aside with invalidation**  
   Item detail is read from Redis when present; on update/delete the cache key is invalidated. This reduces DB load for hot items while keeping data consistent.

5. **Event-driven indexing**  
   Instead of calling Elasticsearch inside the request, the API enqueues a Celery task. The HTTP response is fast and not blocked by search indexing; failures can be retried by the worker.

6. **Configuration via environment**  
   `app/config.py` uses Pydantic Settings so all config is typed and validated at startup. No hardcoded credentials; same code path for local and production with different env vars.

7. **Async end-to-end**  
   FastAPI, SQLAlchemy async, Redis async, and Elasticsearch async allow high concurrency and better resource usage under load.

8. **Security**  
   Passwords are hashed (bcrypt) in `core/security.py`; JWT is used for auth; Bearer token is validated in dependencies. No plain-text passwords in storage or logs.

9. **Operability**  
   Health endpoints support liveness/readiness; Prometheus metrics support monitoring; Docker Compose defines the full stack so the same setup can be used locally and in CI.

Together, these choices support **scalability**, **maintainability**, **testability**, and **operability**, which align with the job’s focus on reliable, scalable web services and best practices.

---

## Quick Start

1. **Clone and set environment**

   ```bash
   cp .env.example .env
   # Edit .env if needed (defaults work with docker-compose).
   ```

2. **Run with Docker Compose**

   ```bash
   docker-compose up --build
   ```

   This starts: API (port 8000), Celery worker, PostgreSQL (5432), Redis (6379), RabbitMQ (5672, management 15672), Elasticsearch (9200), Prometheus (9090), Grafana (3000).

3. **Apply database migrations** (first time or after schema changes)

   ```bash
   docker-compose exec api alembic upgrade head
   ```

4. **Try the API**

   - Docs: http://localhost:8000/docs  
   - Health: http://localhost:8000/api/v1/health  
   - Metrics: http://localhost:8000/metrics  

5. **Optional: run API locally** (with PostgreSQL, Redis, RabbitMQ, Elasticsearch running, e.g. via docker-compose)

   ```bash
   pip install -r requirements.txt
   uvicorn app.main:app --reload
   ```

---

## API Overview

| Method | Path | Description |
|--------|------|-------------|
| GET | /api/v1/health | Liveness |
| GET | /api/v1/health/ready | Readiness |
| POST | /api/v1/users/register | Register (body: email, password, full_name) |
| POST | /api/v1/users/login | Login (body: email, password) → JWT |
| GET | /api/v1/items | List items (paginated: skip, limit) |
| GET | /api/v1/items/{id} | Get item (cached) |
| POST | /api/v1/items | Create item (auth required; body: title, description?, price_cents?, owner_id) |
| PUT | /api/v1/items/{id} | Update item (auth required) |
| DELETE | /api/v1/items/{id} | Delete item (auth required) |
| GET | /api/v1/search/items?q=... | Full-text search (Elasticsearch) |
| GET | /metrics | Prometheus metrics |

---

## Running Tests

- **Unit / API tests (TDD)**  
  ```bash
  pytest tests/ -v
  ```
  Use a local DB or override `DATABASE_URL` (e.g. SQLite in tests via conftest).

- **BDD (pytest-bdd)**  
  ```bash
  pytest tests/step_defs/ tests/features/ -v
  ```

- **With coverage**  
  ```bash
  pytest tests/ -v --cov=app
  ```

---

## Monitoring

- **Prometheus**: http://localhost:9090 (scrapes API `/metrics`).
- **Grafana**: http://localhost:3000 (default login: admin / admin). A Prometheus datasource is provisioned in `monitoring/grafana/provisioning/datasources/`.

You can add custom metrics in the app (e.g. request duration, item create count) and build dashboards in Grafana.

---

## CI/CD

The workflow in `.github/workflows/ci.yml` runs on push/PR to `main` or `develop`:

- Checkout code, set up Python 3.12.
- Start PostgreSQL, Redis, RabbitMQ as services.
- Install dependencies and run pytest.
- Run ruff (lint) and black (format check).

This gives automated testing and basic quality gates; you can extend it with deployment steps (e.g. build image, push to registry, deploy to staging).

---

## Summary

This project provides a single codebase that touches **all** requested and nice-to-have areas: **Python/FastAPI**, **RESTful APIs**, **PostgreSQL**, **Redis**, **Elasticsearch**, **Celery + RabbitMQ**, **Docker/docker-compose**, **TDD/BDD**, **SOLID and clean architecture**, **CI/CD**, and **Prometheus/Grafana**. The README explains which part addresses which challenge and why the design supports scalability, performance, and maintainability.
