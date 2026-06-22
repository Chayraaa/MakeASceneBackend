# Make A Scene
<small>This is the backend of the Make A Scene project.</small>

## Overview

**Make A Scene** is a web application that allows users to discover events and gatherings in their local region.

Unlike traditional event platforms, Make A Scene does **not use any recommendation algorithms**. Instead, it relies on a simple and transparent **tag-based system**:

* Users select their interests via tags
* Their “For You” feed is generated purely from matching events
* No ranking, no engagement optimization, no hidden boosting

This approach ensures that:

* Large and small events are treated equally
* No algorithmic manipulation or "gaming the system" is possible
* Discovery is based purely on relevance, not popularity

In addition to the tag-based feed, users can:

* Search for events
* Filter by location, date, and tags

---

## Event Creation

Artists and event organizers can create events by submitting a structured form.
It's designed to check the good intent of the account by asking for some sort of verification (not yet defined).
This form is then reviewed by a human moderator, who can then grant the ability to create events for that account.

This ensures quality control while preserving creative freedom for organizers.

---

## Architecture

The project follows a **hexagonal architecture (ports & adapters)** approach to maintain separation of concerns and long-term extensibility.

### Tech Stack

* Backend: Flask (Python)
* Database: PostgreSQL
* Object Storage: MinIO (S3-compatible)
* Infrastructure: Docker

---

### Architectural Structure

```
/app
  /routes          -> HTTP layer (Flask controllers)
  /services        -> Business logic layer
  /domain_models   -> Core domain models
  /database_models -> Data access layer implementations
  /repositories    -> External integrations (DB, MinIO, etc.)
    /interfaces    -> protocols for repositories
    /storage       -> everything related to storage (DB, MinIO, etc.)
    /units_of_work -> groups of repositories that work together
```

This structure ensures:

* Framework independence at the core
* Testable business logic
* Clear separation between domain and infrastructure
* Easy future migration or scaling

---

## CI / Quality
![CI](https://github.com/chayraaa/MakeASceneBackend/actions/workflows/ci.yml/badge.svg)

Optional quality tools:

* Test coverage (pytest)
* CI pipeline via GitHub Actions

---

## Motivation & Academic Context

This project originates from a university course at Hof University of Applied Sciences.

The idea was created in coursework with only the requirement to work out a design and improve the idea.
However, it has since evolved into a significantly larger personal project with extended scope due to the personal intent to make the idea a reality.
The whole backend, for example, never was part of the requirements.

This project may be part of a bachelor's thesis at Hof University of Applied Sciences in the future.

---
## AI Disclaimer
Yes, some of the code (especially for deployment) is AI-generated. I am not an expert in everything, so please forgive me.
If there is someone willing to update/help with this, you are more than welcome!

---
## License

TBD
