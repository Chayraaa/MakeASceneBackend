# Make A Scene Backend — Developer Guide

A reference for new developers to understand the project structure, find what they need, and add new features correctly.

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Tech Stack](#2-tech-stack)
3. [Project Structure](#3-project-structure)
4. [Architecture: Hexagonal (Ports & Adapters)](#4-architecture-hexagonal-ports--adapters)
5. [Running the Project](#5-running-the-project)
6. [Where to Find What](#6-where-to-find-what)
   - [Routes / Endpoints](#routes--endpoints)
   - [Business Logic](#business-logic)
   - [Database Tables & ORM](#database-tables--orm)
   - [Domain Entities](#domain-entities)
   - [Repository Interfaces](#repository-interfaces)
   - [Repository Implementations](#repository-implementations)
   - [External Services](#external-services)
   - [Dependency Injection](#dependency-injection)
   - [Auth & Middleware Decorators](#auth--middleware-decorators)
   - [Tests](#tests)
   - [Migrations](#migrations)
7. [All Current Endpoints](#7-all-current-endpoints)
8. [How to Add a New Feature](#8-how-to-add-a-new-feature)
9. [Authentication Flow](#9-authentication-flow)
10. [Configuration & Environment Variables](#10-configuration--environment-variables)
11. [Docker Services](#11-docker-services)

---

## 1. Project Overview

**Make A Scene** is an event discovery platform backend. It uses a **transparent tag-based system** (no black-box recommendation algorithms) to match users with events. Users subscribe to or block tags; the system surfaces relevant content accordingly.

The backend is a **Flask REST API** backed by PostgreSQL, with MinIO for image storage, Typesense for semantic search, and Ollama for LLM features.

---

## 2. Tech Stack

| Role | Technology |
|------|-----------|
| HTTP Framework | Flask |
| Database | PostgreSQL |
| ORM + Migrations | Flask-SQLAlchemy + Flask-Migrate (Alembic) |
| Search Engine | Typesense |
| Image Storage | MinIO (S3-compatible) |
| Email Delivery | Resend |
| Authentication | PyJWT + Argon2 password hashing |
| OAuth | Authlib (Google OAuth 2.0) |
| Request Validation | openapi-core (validates against OpenAPI spec) |
| NLP / Embeddings | NLTK |
| LLM | Ollama (gemma2:9b, qwen2.5:1.5b) |
| Testing | pytest + pytest-mock |
| API Docs | Flask-Swagger-UI |
| WSGI Server | gunicorn |

---

## 3. Project Structure

```
S:\MakeASceneBackend/
├── app/
│   ├── __init__.py                  # App factory (create_app) + decorators
│   ├── extensions.py                # Shared Flask extensions (db, migrate, typesense_client)
│   ├── routes/                      # HTTP layer — Flask blueprints
│   │   ├── health.py
│   │   ├── auth.py
│   │   ├── user.py
│   │   ├── tag.py
│   │   ├── site_account.py
│   │   └── image.py
│   ├── services/                    # Business logic — framework-independent
│   │   ├── auth_service.py
│   │   ├── user_service.py
│   │   ├── password_service.py
│   │   ├── tag_service.py
│   │   ├── site_account_service.py
│   │   ├── image_service.py
│   │   └── google_oauth_service.py
│   ├── domain_models/               # Core entities — plain Python dataclasses
│   │   ├── user.py
│   │   ├── auth/
│   │   ├── tags/
│   │   └── site_account/
│   ├── database_models/             # SQLAlchemy ORM models
│   │   ├── user_model.py
│   │   ├── auth/
│   │   ├── tags/
│   │   └── site_account/
│   ├── repositories/
│   │   ├── interfaces/
│   │   │   ├── storage/             # Protocols for data repos (the "ports")
│   │   │   └── external/            # Protocols for external services (email, search)
│   │   ├── storage/                 # SQL + in-memory repo implementations
│   │   │   ├── auth/
│   │   │   ├── tags/
│   │   │   ├── site_account/
│   │   │   └── image/
│   │   ├── external/                # Resend email + Typesense search implementations
│   │   └── units_of_work/
│   │       ├── deploy_unit.py       # Production DI — wires all real repos together
│   │       └── test_unit.py         # Test DI — swaps in-memory/mock repos
│   ├── helper/
│   │   └── llm/                     # Tag expander using Ollama
│   └── static/                      # OpenAPI spec (YAML)
├── tests/
│   ├── conftest.py                  # Shared pytest fixtures
│   ├── unit/                        # Service tests with mocked repos
│   └── integration/                 # Repository tests with real DB
├── migrations/
│   └── versions/                    # Alembic migration files
├── k8s/                             # Kubernetes manifests
├── docker-compose.yaml
├── Dockerfile
├── docker-entrypoint.sh
├── run.py                           # Entry point: calls create_app() and runs the app
├── requirements.txt
├── normal.env                       # Non-secret config
├── secrets.env                      # Secret config (not committed)
├── test.env                         # Test environment config
├── migrate.sh / migrate.ps1         # Migration helper scripts
└── populate_tags.sh / .ps1          # Seed tags helper scripts
```

---

## 4. Architecture: Hexagonal (Ports & Adapters)

The project enforces a clean separation between business logic and infrastructure. There are four layers:

```
  HTTP (routes/)
       ↓
  Services (services/)         ← business logic, depends only on protocols
       ↓
  Protocols (repositories/interfaces/)   ← abstract interfaces ("ports")
       ↓
  Implementations (repositories/storage/ + repositories/external/)  ← "adapters"
```

**Key consequence:** services never import SQLAlchemy, MinIO, Typesense, etc. directly. They accept repository objects that match a Protocol. This makes unit testing trivial — just pass in a mock.

### Domain Models vs Database Models

| | Location | Purpose |
|-|----------|---------|
| **Domain models** | `app/domain_models/` | Plain Python `@dataclass`. Used inside services. No framework imports. |
| **Database models** | `app/database_models/` | SQLAlchemy `db.Model` subclasses. Only used inside repositories. |

Repositories are responsible for the conversion:

```python
# Inside a repository:
db_user = self.session.get(UserModel, user_id)        # SQLAlchemy model
return User(id=db_user.id, email=db_user.email, ...)  # Domain model
```

Services never see `UserModel` — they only ever see `User`.

---

## 5. Running the Project

### With Docker (recommended)

```bash
docker compose up
```

This starts all five services (see [Docker Services](#11-docker-services)).

### Environment setup

Copy and fill in:
- `normal.env` — non-secret settings (DB URI, base URL, Typesense host, MinIO user)
- `secrets.env` — secrets (JWT secret, API keys, MinIO password, Google OAuth)

### Running migrations

```bash
# Unix
bash migrate.sh

# PowerShell
./migrate.ps1
```

Or manually:
```bash
FLASK_ENV=migration flask db upgrade
```

### Seeding tags

```bash
bash populate_tags.sh
# or
./populate_tags.ps1
```

### Running tests

```bash
pytest
pytest --cov=app tests/   # with coverage
```

---

## 6. Where to Find What

### Routes / Endpoints

**Location:** `app/routes/`

Each file is a Flask Blueprint. Blueprints are registered in `app/__init__.py` inside `setup_routes()` with a `/v1` prefix.

| File | Blueprint prefix | Covers |
|------|-----------------|--------|
| `health.py` | `/v1/health` | Health check |
| `auth.py` | `/v1/auth` | Login, logout, OAuth, email confirm, password reset |
| `user.py` | `/v1/users` | User CRUD, saved/blocked tags |
| `tag.py` | `/v1/tags` | Tag search, autocomplete, lookup |
| `site_account.py` | `/v1/site_accounts` | Site account CRUD + applications |
| `image.py` | `/v1/image` | Image streaming from MinIO |

To add a new endpoint, create a new route file (or add to an existing one), then register it in `setup_routes()`.

### Business Logic

**Location:** `app/services/`

| File | Service class | Responsibility |
|------|--------------|---------------|
| `user_service.py` | `UserService` | Register, fetch, update, delete users |
| `auth_service.py` | `AuthService` | Login, refresh, logout, email confirm, password reset |
| `password_service.py` | `PasswordService` | Hashing, JWT generation (static methods) |
| `tag_service.py` | `TagService` | Create/search/subscribe/block tags |
| `site_account_service.py` | `SiteAccountService` | Site account CRUD, applications |
| `image_service.py` | `ImageService` | Fetch/save images from/to MinIO |
| `google_oauth_service.py` | `GoogleOAuthService` | Google OAuth user creation and token exchange |

Services are instantiated once in `setup_services()` (in `app/__init__.py`) and attached to the Flask `app` object (e.g., `app.user_service`). Routes access them via `current_app.user_service`.

### Database Tables & ORM

**Location:** `app/database_models/`

| File | Table(s) |
|------|---------|
| `user_model.py` | `users` |
| `auth/confirm_token_model.py` | `confirm_tokens` |
| `auth/refresh_token_model.py` | `refresh_tokens` |
| `auth/password_reset_token_model.py` | `password_reset_tokens` |
| `tags/tag_model.py` | `tags` (self-referential parent/child) |
| `tags/saved_tags_model.py` | `saved_tags` (user ↔ tag many-to-many) |
| `tags/blocked_tags_model.py` | `blocked_tags` (user ↔ tag many-to-many) |
| `site_account/site_account_model.py` | `site_accounts` |
| `site_account/site_account_application_model.py` | `site_account_applications` |
| `site_account/site_account_application_contact_model.py` | `site_account_application_contacts` |
| `site_account/site_account_application_sources_model.py` | `site_account_application_sources` |

### Domain Entities

**Location:** `app/domain_models/`

| File | Entity | Key fields |
|------|--------|-----------|
| `user.py` | `User`, `Role` (enum) | `id`, `email`, `role`, `confirmed`, `oauth` |
| `tags/tag.py` | `Tag` | `id`, `name`, `parent` |
| `tags/saved_tag.py` | `SavedTag` | `user_id`, `tag_id` |
| `tags/blocked_tag.py` | `BlockedTag` | `user_id`, `tag_id` |
| `auth/refresh_token.py` | `RefreshToken` | `id`, `hashed_token`, `expires_at`, `revoked` |
| `auth/confirm_token.py` | `ConfirmToken` | same pattern |
| `auth/password_reset_token.py` | `PasswordResetToken` | same pattern |
| `site_account/SiteAccount.py` | `SiteAccount` | `id`, `name`, `creator_id`, `layout` |
| `site_account/SiteAccountApplication.py` | `SiteAccountApplication` | application fields |

`Role` enum (in `user.py`):
```python
class Role(Enum):
    USER = 0
    MODERATOR = 1
    ADMIN = 2
```

### Repository Interfaces

**Location:** `app/repositories/interfaces/`

These are Python `Protocol` classes — they define the contract a repository must fulfill without coupling services to any particular implementation.

```
interfaces/
├── storage/
│   ├── user_repo_protocol.py
│   ├── image_storage_protocol.py
│   ├── auth/
│   │   ├── confirm_token_repo_protocol.py
│   │   ├── refresh_token_repo_protocol.py
│   │   └── password_reset_token_repo_protocol.py
│   ├── tags/
│   │   ├── tag_repo_protocol.py
│   │   ├── saved_tag_repo_protocol.py
│   │   └── blocked_tag_repo_protocol.py
│   └── site_account/
│       ├── site_account_repo_protocol.py
│       └── site_account_application_repo_protocol.py
└── external/
    ├── email_protocol.py
    ├── search_engine_tag_protocol.py
    └── search_engine_site_account_protocol.py
```

When you add a new repository, **always define a protocol first**. Services accept the protocol type, not the concrete class.

### Repository Implementations

**Location:** `app/repositories/storage/` and `app/repositories/external/`

| Protocol | SQL implementation | In-memory/mock |
|----------|--------------------|---------------|
| `UserRepoProtocol` | `sql_user_repo.py` | `mem_user_repo.py` |
| `ImageStorageProtocol` | `image/minio_image_storage.py` | `image/mem_image_storage.py` |
| Tag repos | `tags/sql_*.py` | — |
| Site account repos | `site_account/sql_*.py` | — |
| Auth token repos | `auth/sql_*.py` | — |
| `EmailProtocol` | `external/resend_email_repo.py` | — |
| `SearchEngineTagProtocol` | `external/search_engine/typesense_tag_search_repo.py` | — |
| `SearchEngineSiteAccountProtocol` | `external/search_engine/typesense_site_account_search_repo.py` | — |

### External Services

| Service | File | Notes |
|---------|------|-------|
| Email | `repositories/external/resend_email_repo.py` | Uses Resend.dev HTTP API |
| Tag search | `repositories/external/search_engine/typesense_tag_search_repo.py` | Semantic search via NLTK embeddings |
| Site account search | `repositories/external/search_engine/typesense_site_account_search_repo.py` | |
| LLM tag expansion | `helper/llm/tag_expander.py` + `expansion_worker.py` | Uses local Ollama |

### Dependency Injection

**Location:** `app/repositories/units_of_work/`

This is where concrete repository implementations are wired together and handed to services.

| File | Used when |
|------|----------|
| `deploy_unit.py` | Production — uses PostgreSQL, MinIO, Resend, Typesense |
| `test_unit.py` | Tests — uses in-memory image storage, no real external services |

`setup_services()` in `app/__init__.py` does:
```python
unit = DeployUnitOfWork()   # or TestUnitOfWork() if testing=True
app.user_service = UserService(unit.user_repo, unit.email_repo, ...)
app.auth_service = AuthService(unit.user_repo, unit.refresh_token_repo, ...)
# ...
```

When you add a new service, add its instantiation here.

### Auth & Middleware Decorators

**Location:** `app/__init__.py`

Two key decorators applied to route functions:

**`@login_required(role)`**
- Reads the `Authorization: Bearer <token>` header
- Validates the JWT
- Fetches the user from the database
- Enforces minimum role (e.g., `Role.MODERATOR`)
- Injects the `User` object into the route function

```python
@user_bp.route("/me", methods=["GET"])
@login_required(Role.USER)
def get_me(user: User):
    ...
```

**`@validate`**
- Validates the request body against the OpenAPI spec
- Returns `422 Unprocessable Entity` on failure
- The spec lives in `app/static/`

### Tests

**Location:** `tests/`

| Directory | What to put here |
|-----------|-----------------|
| `tests/unit/` | Service tests — mock all repositories with `MagicMock` |
| `tests/integration/` | Repository tests — use real SQLite database from `conftest.py` fixtures |

Key fixtures (from `conftest.py`):
- `app` — creates a test Flask app with SQLite in-memory DB, calls `db.create_all()`
- `session` — provides a transaction-scoped database session

---

## 7. All Current Endpoints

All routes are under `/v1`.

### Health
| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/v1/health/` | None | Returns `{"status": "ok"}` |

### Auth (`/v1/auth`)
| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/sessions` | None | Login (email+password or refresh token) |
| POST | `/logout` | Required | Revoke all refresh tokens |
| GET | `/oauth/redirect?auth=google` | None | Redirect to Google OAuth |
| GET | `/oauth/google/callback` | None | Google OAuth callback |
| POST | `/oauth/exchange` | None | Exchange OAuth code for JWT |
| GET | `/email/confirm?token=X` | None | Confirm email address |
| POST | `/email/resend` | None | Resend confirmation email |
| POST | `/password/request-reset` | None | Send password reset email |
| POST | `/password/reset` | None | Reset password with token |

### Users (`/v1/users`)
| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/` | None | Register new user |
| GET | `/me` | USER | Get current user info |
| PATCH | `/me` | USER | Update user settings |
| DELETE | `/me` | USER | Delete account |
| GET | `/me/tags` | USER | Get saved tags (paginated) |
| POST | `/me/tags/<id>` | USER | Subscribe to tag |
| DELETE | `/me/tags/<id>` | USER | Unsubscribe from tag |
| GET | `/me/tags/block` | USER | Get blocked tags (paginated) |
| POST | `/me/tags/block/<id>` | USER | Block a tag |
| DELETE | `/me/tags/block/<id>` | USER | Unblock a tag |

### Tags (`/v1/tags`)
| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/?query=X` | None | Search or autocomplete tags |
| GET | `/<id>` | None | Get tag by ID |

### Site Accounts (`/v1/site_accounts`)
| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/` | None | Search site accounts (paginated) |
| POST | `/` | MODERATOR | Create site account |
| GET | `/<id>` | None | Get site account details |
| PATCH | `/<id>` | Owner/Mod | Update site account |
| DELETE | `/<id>` | Owner/Mod | Delete site account |
| POST | `/application` | USER | Apply for site account creator status |
| GET | `/application` | MODERATOR | List all applications |
| GET | `/application/<id>` | USER | Get specific application |
| PATCH | `/application/<id>` | USER | Update application |
| DELETE | `/application/<id>` | USER | Delete application |

### Images (`/v1/image`)
| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/<path:key>` | None | Stream image from MinIO |

---

## 8. How to Add a New Feature

Follow the hexagonal architecture. Use the existing features (e.g., `site_account`) as a reference. The steps below add a hypothetical "Venue" feature.

### Step 1 — Domain Model

`app/domain_models/venue.py`
```python
from dataclasses import dataclass

@dataclass
class Venue:
    id: int
    name: str
    location: str
```

No Flask or SQLAlchemy imports here.

### Step 2 — Database Model

`app/database_models/venue_model.py`
```python
from app.extensions import db
from sqlalchemy.orm import Mapped, mapped_column

class VenueModel(db.Model):
    __tablename__ = "venues"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(unique=True, nullable=False)
    location: Mapped[str] = mapped_column(nullable=False)
```

### Step 3 — Repository Protocol

`app/repositories/interfaces/storage/venue_repo_protocol.py`
```python
from typing import Protocol
from app.domain_models.venue import Venue

class VenueRepoProtocol(Protocol):
    def get_venue(self, venue_id: int) -> Venue | None: ...
    def create_venue(self, name: str, location: str) -> bool: ...
    def delete_venue(self, venue: Venue) -> bool: ...
```

### Step 4 — Repository Implementation

`app/repositories/storage/sql_venue_repo.py`
```python
from app.database_models.venue_model import VenueModel
from app.domain_models.venue import Venue

class SqlVenueRepo:
    def __init__(self, session):
        self.session = session

    def get_venue(self, venue_id: int) -> Venue | None:
        row = self.session.get(VenueModel, venue_id)
        if not row:
            return None
        return Venue(id=row.id, name=row.name, location=row.location)

    def create_venue(self, name: str, location: str) -> bool:
        self.session.add(VenueModel(name=name, location=location))
        self.session.commit()
        return True

    def delete_venue(self, venue: Venue) -> bool:
        row = self.session.get(VenueModel, venue.id)
        if row:
            self.session.delete(row)
            self.session.commit()
        return True
```

### Step 5 — Service

`app/services/venue_service.py`
```python
from app.repositories.interfaces.storage.venue_repo_protocol import VenueRepoProtocol
from app.domain_models.venue import Venue

class VenueService:
    def __init__(self, venue_repo: VenueRepoProtocol):
        self.venue_repo = venue_repo

    def get_venue(self, venue_id: int) -> Venue | None:
        return self.venue_repo.get_venue(venue_id)

    def create_venue(self, name: str, location: str) -> bool:
        return self.venue_repo.create_venue(name, location)
```

### Step 6 — Routes

`app/routes/venue.py`
```python
from flask import Blueprint, current_app
from app.domain_models.user import Role

venue_bp = Blueprint("venue", __name__)

@venue_bp.route("/<int:venue_id>", methods=["GET"])
def get_venue(venue_id: int):
    venue = current_app.venue_service.get_venue(venue_id)
    if not venue:
        return {"error": "not found"}, 404
    return {"id": venue.id, "name": venue.name, "location": venue.location}

@venue_bp.route("/", methods=["POST"])
@login_required(Role.MODERATOR)
def create_venue(user):
    # parse body, call service
    ...
```

### Step 7 — Wire into Units of Work

In `app/repositories/units_of_work/deploy_unit.py`:
```python
from app.repositories.storage.sql_venue_repo import SqlVenueRepo

class DeployUnitOfWork:
    def __init__(self):
        # ... existing repos ...
        self.venue_repo = SqlVenueRepo(db.session)
```

Do the same in `test_unit.py`.

### Step 8 — Instantiate Service & Register Blueprint

In `app/__init__.py`:

```python
# In setup_services():
from app.services.venue_service import VenueService
app.venue_service = VenueService(unit.venue_repo)

# In setup_routes():
from app.routes.venue import venue_bp
app.register_blueprint(venue_bp, url_prefix="/v1/venues")
```

### Step 9 — Create a Migration

```bash
FLASK_ENV=migration flask db migrate -m "add venues table"
FLASK_ENV=migration flask db upgrade
```

### Step 10 — Write Tests

Unit test (`tests/unit/test_venue_service.py`):
```python
from unittest.mock import MagicMock
from app.services.venue_service import VenueService

def test_get_venue_calls_repo():
    repo = MagicMock()
    service = VenueService(repo)
    service.get_venue(1)
    repo.get_venue.assert_called_once_with(1)
```

Integration test (`tests/integration/test_venue_repository.py`):
```python
from app.repositories.storage.sql_venue_repo import SqlVenueRepo

def test_create_and_get_venue(app):
    with app.app_context():
        from app.extensions import db
        repo = SqlVenueRepo(db.session)
        repo.create_venue("Madison Square Garden", "New York")
        venue = repo.get_venue(1)
        assert venue.name == "Madison Square Garden"
```

---

## 9. Authentication Flow

```
POST /v1/users/            → register (returns nothing, sends confirmation email)
GET  /v1/auth/email/confirm?token=X  → confirm email
POST /v1/auth/sessions     → login → { access_token, refresh_token }

# Protected requests:
GET /v1/users/me
  Authorization: Bearer <access_token>

# When access token expires:
POST /v1/auth/sessions  { refresh_token: "..." }  → new access_token + refresh_token
```

**Tokens:**
- **Access token** — JWT, 24-hour lifetime, contains `user_id`
- **Refresh token** — long random string, stored hashed in DB, used to get new access token
- **Confirm token** — sent by email, verifies email address
- **Reset token** — sent by email for password resets
- **Exchange token** — 1-minute JWT used during Google OAuth flow

**`@login_required(role)`** reads `Authorization: Bearer <token>`, decodes the JWT using `JWT_SECRET`, fetches the user, checks the role, then calls the route handler with the `User` object injected as the first argument.

---

## 10. Configuration & Environment Variables

| Variable | File | Description |
|----------|------|-------------|
| `SQLALCHEMY_DATABASE_URI` | `normal.env` | PostgreSQL connection string |
| `BASE_URL` | `normal.env` | Public URL (used in email links, image URLs) |
| `TYPESENSE_HOST` | `normal.env` | Typesense service hostname |
| `TYPESENSE_DATA_DIR` | `normal.env` | Typesense data directory |
| `MINIO_ROOT_USER` | `normal.env` | MinIO access key |
| `JWT_SECRET` | `secrets.env` | Secret for signing JWTs |
| `TYPESENSE_API_KEY` | `secrets.env` | Typesense admin API key |
| `MINIO_ROOT_PASSWORD` | `secrets.env` | MinIO secret key |
| `GOOGLE_CLIENT_ID` | `secrets.env` | Google OAuth client ID |
| `GOOGLE_CLIENT_SECRET` | `secrets.env` | Google OAuth client secret |

`FLASK_ENV` controls startup behavior:
- (default) — production mode
- `migration` — uses alternate DB URI for running Alembic migrations
- `setup` — initializes Typesense schema and loads tags from `tags.txt`

---

## 11. Docker Services

Defined in `docker-compose.yaml`. All communicate on an internal Docker network.

| Service | Image | Port(s) | Purpose |
|---------|-------|---------|---------|
| `backend` | (built from Dockerfile) | `5000` | Flask app |
| `db` | `postgres:18-alpine` | `5432` | PostgreSQL database |
| `minio` | MinIO | `9000`, `9001` | S3-compatible image storage (9001 = admin console) |
| `typesense` | Typesense | `8108` | Semantic search engine |
| `ollama` | Ollama | `11434` | Local LLM (gemma2:9b, qwen2.5:1.5b) |

`backend` depends on `db` (healthcheck: `pg_isready`), `minio`, and `typesense` (healthcheck: HTTP `/health`) being healthy before starting.

Data is persisted in named volumes: `postgres_data`, `minio_data`, `typesense_data`, `ollama_data`.

---

*This guide covers the structure as it exists at the time of writing. When in doubt, the code is the source of truth.*
