# task-manager-api

[![MIT License](https://img.shields.io/badge/license-MIT-brightgreen)](LICENSE)
[![Docker Image](https://img.shields.io/badge/docker-ready-blue)](#)

---

## Short description

A production-oriented **Django REST API** for task and project management built with JWT auth, background processing (Celery + Redis), and a Docker-first development setup. This repository is intended as a realistic, deployable reference implementation for team task management and for learning production patterns (Docker, Celery, Postgres, Swagger).

---

## Why this project exists (Problem & Audience)

Many example task managers show CRUD only. This project demonstrates a fuller stack needed for real applications:

* background job processing (notifications, recurring tasks) with Celery;
* robust persistence with Postgres;
* containerized development and CI-friendly architecture;
* clear API documentation via Swagger for integrators.

**Audience:** backend engineers, DevOps learners, architects who want a small but realistic example of a production-ready Django API.

---

## Key features (what actually matters)

* **JWT authentication** (access + refresh tokens).
* **Role-aware users** (basic differentiation between regular users and admins — extendable to RBAC).
* **Task & Project models** with relationships and simple scheduling metadata (due dates, priority, status).
* **Background jobs with Celery** for async tasks (email notifications, scheduled/recurring tasks) using **Redis** as broker & result backend.
* **Docker-first**: compose file to run app + Postgres + Redis + Celery worker + Celery beat.
* **Interactive Swagger UI** for endpoint exploration and quick testing.
* **Tests & CI friendly**: tests included and can be run in CI.

> Note: These are implemented as realistic examples rather than abstract placeholders — e.g., notification tasks, database migrations on boot (with idempotency), and health checks are considered in the compose setup.

---

## Quick Start — Development (Docker)

Prerequisites: Docker & docker-compose installed.

1. Copy example env and update secrets:

```bash
cp .env.example .env
# edit .env and set the required variables
```

2. Build and start the stack:

```bash
docker-compose up --build
```

3. Open the Swagger UI to explore the API:

```
http://localhost:8000/swagger/
```

### Useful commands (local development)

Open a shell inside the web container:

```bash
docker-compose exec web sh
# or bash if available
```

Run migrations manually if needed:

```bash
python manage.py makemigrations
python manage.py migrate
```

Run tests inside the web container:

```bash
docker-compose exec web python -m pytest
```

---

## Environment variables

Create a `.env` file in the project root. Required vs optional keys are listed.

**Required (must be set)**

```
# Django
SECRET_KEY=your-secret-key
DEBUG=1 # 0 in production
ALLOWED_HOSTS=localhost,127.0.0.1

# PostgreSQL
POSTGRES_DB=app_db
POSTGRES_USER=app_user
POSTGRES_PASSWORD=strongpassword
POSTGRES_HOST=db
POSTGRES_PORT=5432

# Redis/Celery
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/1

# Email (for notifications)
EMAIL_HOST=
EMAIL_PORT=
EMAIL_HOST_USER=
EMAIL_HOST_PASSWORD=
DEFAULT_FROM_EMAIL=

# JWT config, other app settings can be provided as environment variables
```

**Security note:** Do **not** commit `.env` to source control. Use secrets manager in production and rotate `SECRET_KEY` and DB passwords regularly.

---

## Example API usage (curl)

Authenticate and obtain tokens:

```bash
curl -X POST "http://localhost:8000/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username":"alice","password":"password"}'
```

Response example:

```json
{ "access": "<jwt-access>", "refresh": "<jwt-refresh>" }
```

Create a task (use access token):

```bash
curl -X POST "http://localhost:8000/api/tasks" \
  -H "Authorization: Bearer <jwt-access>" \
  -H "Content-Type: application/json" \
  -d '{"title":"Write README","description":"Finish improved README","due_date":"2026-01-15"}'
```

List tasks:

```bash
curl -X GET "http://localhost:8000/api/tasks" -H "Authorization: Bearer <jwt-access>"
```

Register a user:

```bash
curl -X POST "http://localhost:8000/api/users" -H "Content-Type: application/json" -d '{"username":"bob","password":"p@ssw0rd","email":"bob@example.com"}'
```

---

## Architecture (high-level)

* **Django**: REST API (Django REST Framework) implementing endpoints for users, auth, tasks, projects.
* **Postgres**: primary relational datastore.
* **Redis**: Celery broker and result backend. Also usable as cache.
* **Celery workers**: asynchronous processing, separate container for workers.
* **Celery Beat**: periodic tasks scheduler for recurring jobs.
* **Docker Compose**: orchestrates services for development and simple staging.

For more in-depth diagrams and the exact compose layout, see `docs/architecture.md` (recommended) or the `docker-compose.yml` in the repo.

**Operational note:** `depends_on` does not guarantee readiness. The compose file includes healthchecks and the application performs DB readiness checks on startup (or you can use a small `wait-for` helper script).

---

## Production considerations (short checklist)

* Use a WSGI server (e.g., `gunicorn`) behind a reverse proxy (e.g., Nginx). Do not use `runserver` in production.
* Serve static files with a CDN or object storage (S3) or via Nginx + `collectstatic`.
* Use a secrets manager (Vault, AWS Secrets Manager) — do not store secrets in `.env` on disk.
* Configure secure TLS on the proxy; enforce HSTS.
* Tune Postgres and Celery concurrency for expected load.
* Log aggregation and monitoring (filebeat / vector + ELK / Prometheus + Grafana).
* Configure email provider with retries and error handling for notification tasks.

---

## Troubleshooting

* **App fails to connect to DB on startup:** ensure Postgres container is healthy and `POSTGRES_HOST` points to the service name. Use `docker-compose logs db` to inspect.
* **Migrations fail in CI/CD:** ensure DB user has permission to create/migrate and that migrations are deterministic.
* **Celery tasks not executing:** confirm `CELERY_BROKER_URL` is correct, the worker container is running, and the queue names match.

---

## Tests

Run tests locally inside the web container:

```bash
docker-compose exec web python -m pytest
```

CI suggestion: run tests against a dedicated Postgres + Redis test services and collect coverage.

---

## Contributing

1. Fork the repository.
2. Create a feature branch: `git checkout -b feat/my-change`.
3. Run tests and linters locally.
4. Open a Pull Request with a clear description and tests for behavior changes.

Please follow the existing code style and keep migrations and requirements updated.

---

## Files & locations you may care about

* `docker-compose.yml` — primary compose file used in local dev.
* `core/` — Django project root (settings, celery app).
* `apps/tasks/` — task and project models, serializers, views.
* `apps/users/` — user and authentication code.
* `docs/architecture.md` — (recommended) deeper architecture notes and diagrams.

---

## LICENSE

This project is licensed under the MIT License. See the `LICENSE` file for details.

---

## Maintainer / Contact

Seyyed Ali Bargh — maintainers listed in the repository. Update `LICENSE` and this section if you change copyright owner/year.

---

## Changelog of README improvements

* Made value proposition explicit (who this is for and what problem it solves).
* Moved low-level container details out of the overview and into architecture / docs.
* Added example `.env` guidance and required vs optional split.
* Added concrete curl examples for quick testing.
* Added production checklist and troubleshooting pointers to reduce questions from integrators.

---

If you want, I can also:

* produce a short `CONTRIBUTING.md` or `docs/architecture.md`,
* convert this README to Persian, or
* shorten it to a one-page `README` with a `docs/` folder for the rest.
