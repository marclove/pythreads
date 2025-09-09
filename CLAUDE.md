# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

PyThreads uses **uv** for package management and development:

- **Setup**: `uv sync --dev` - Install all dependencies including dev extras
- **Lint**: `uv run ruff check --fix .` - Run linter with auto-fix
- **Type checking**: `uv run pyright .` - Run type checking
- **Unit tests (no network)**: `CI=1 uv run pytest -m "not smoke"` - Run offline tests only
- **All tests**: `uv run pytest` - Run all tests including network-dependent smoke tests
- **Documentation**: `uv run sphinx-build -b html docs/source docs/build/html` - Build docs
- **Coverage**: `uv run pytest --cov` - Run tests with coverage report

## Architecture

PyThreads is a Python wrapper for Meta's Threads API with a layered architecture:

### Core Authentication Layer (`src/pythreads/`)
- **`threads.py`**: Main `Threads` class for OAuth2 flow - handles authorization URL generation, token exchange, and refresh
- **`credentials.py`**: `Credentials` class for token management with expiration checking
- **`configuration.py`**: `Configuration` class for app settings (app_id, secret, redirect_uri, scopes)

### API Client Layer (`src/pythreads/api/`)
- **`client.py`**: Main `API` class - async HTTP client with session management, retries, and service orchestration
- **`transport.py`**: `Transport` class - low-level HTTP transport with URL building and request handling
- **Service endpoints** in `endpoints/`: Modular services for different API domains:
  - `accounts.py`: User profile and publishing limits
  - `threads.py`: Thread/post listing with async iterators for pagination
  - `media.py`: Container creation, status checking, and publishing
  - `insights.py`: Analytics and metrics
  - `moderation.py`: Reply management (hide/unhide)

### Type System (`src/pythreads/api/`)
- **`types.py`**: Enums, dataclasses, and constants for API parameters and responses
- **`models.py`**: Optional Pydantic v2 models for response validation (requires `[models]` extra)
- **`errors.py`**: Custom exception classes for API and HTTP errors

### Key Design Patterns
- **Async context manager**: `API` object manages aiohttp sessions automatically
- **Service delegation**: Main `API` class delegates to specialized service classes
- **Optional session management**: Users can provide their own aiohttp session or let the library manage it
- **Retry logic**: Built-in exponential backoff for transient HTTP errors
- **Paginated iterators**: Async generators for seamless multi-page data fetching

### Publishing Workflow
Threads API requires a two/three-step publishing process:
1. Create container(s) for media/text
2. Wait for video processing (if applicable) 
3. Publish container

For carousels: Create individual media containers → Create carousel container → Publish carousel

## Environment Variables
Required for API functionality:
- `THREADS_APP_ID`: Meta app ID
- `THREADS_API_SECRET`: Meta app secret  
- `THREADS_REDIRECT_URI`: OAuth2 redirect URI

Optional:
- `THREADS_GRAPH_API_VERSION`: API version (defaults to latest)
- `THREADS_SSL_CERT_FILEPATH` / `THREADS_SSL_KEY_FILEPATH`: SSL client certificates

## Testing Strategy
- **Unit tests**: Mock-based tests in `tests/` directory
- **Smoke tests**: Real API integration tests (marked with `@pytest.mark.smoke`)
- **CI environment**: Set `CI=1` to skip network-dependent smoke tests
- **Coverage**: Maintained at 93%+ as shown in README badge

## Optional Dependencies
- **`[models]`**: Pydantic v2 models for response validation
- **`[dev]`**: All development tools (pytest, ruff, pyright, sphinx, etc.)