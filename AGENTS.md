# AI Workforce Intelligence - Agent Instructions

## Project Goal

Build a simple AI Workforce Intelligence Platform focused on functionality and integrations rather than excessive enterprise complexity.

## Architecture

Use the existing layered architecture:

API → Service → Repository → Database

Keep responsibilities separated:

- API: HTTP routes, request/response handling
- Schemas: Pydantic validation
- Services: business logic
- Repositories: database access
- Models: SQLAlchemy database models
- Integrations: external APIs and services
- AI: AI-related logic
- Tests: automated tests

## Current Stack

- Python
- FastAPI
- PostgreSQL
- SQLAlchemy 2.x
- Alembic
- Pydantic Settings

## Development Rules

- Keep the implementation simple and practical.
- Do not add unnecessary tables, abstractions, frameworks, or dependencies.
- Reuse existing architecture and code where possible.
- Do not rewrite working code unnecessarily.
- Do not modify unrelated functionality.
- Use modern SQLAlchemy 2.x typed mappings.
- Use environment variables for secrets and configuration.
- Never hardcode API keys, passwords, or secrets.
- Database schema changes must use Alembic migrations.
- Do not automatically apply migrations unless explicitly requested.
- Add tests for new functionality.
- Run tests and relevant validation after making changes.
- Do not commit changes unless explicitly requested.

## Project Workflow

For each feature:

1. Inspect existing code and documentation.
2. Explain the implementation plan.
3. Implement the feature.
4. Run tests and validation.
5. Fix discovered issues.
6. Report files changed and verification results.

## Scope Control

The project should prioritize:

- Core functionality
- Clean backend architecture
- API integrations
- AI functionality
- Practical demonstrations of modern development skills

Do not turn the project into an unnecessarily large enterprise system.
