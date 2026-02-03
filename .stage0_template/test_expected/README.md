# api_utils

This repo builds and publishes a shared PyPI library used across the [Creator Dashboard](https://github.com/agile-crafts-people/CreatorDashboard) system.

## ⚠️ Security Requirements

**CRITICAL:** `JWT_SECRET` must be explicitly set before using api_utils in any environment. The application will fail to start if `JWT_SECRET` is not configured.

```bash
# For development/testing
export JWT_SECRET='your-development-secret'

# For production (use strong, randomly generated secret)
export JWT_SECRET=$(openssl rand -base64 32)
```

**Never use the default JWT_SECRET value in any environment.** See [SECURITY.md](./SECURITY.md) for complete security guidance.

## Prerequisites
- Python [v3.14](https://www.python.org/downloads/)
- pipenv [v2026.0.3](https://pipenv.pypa.io/en/latest/installation.html) or newer 
- [MongoDB Compass](https://www.mongodb.com/docs/compass/install/?operating-system=linux&package-type=.deb) (optional - connection string is localhost://mongodb:27017)

## Developer Commands

```bash
## Install dependencies
pipenv install

# start backing db container (required for MongoIO unit/integration tests)
pipenv run db

## run unit tests (includes MongoIO Integration Tests)
pipenv run test

## run demo dev server - captures command line, serves API at localhost:8080
## Note: ENABLE_LOGIN=true is automatically set by the dev script
pipenv run dev

## run E2E tests (assumes running API at localhost:8080)
pipenv run e2e

## build package for deployment
pipenv run build

## format code
pipenv run format

## lint code
pipenv run lint
```

## Project Structure

- `api_utils/` - Main package containing:
  - `config/` - Configuration singleton with support for file, environment, and default values
  - `flask_utils/` - Flask-specific utilities (JSON encoder, token, breadcrumb)
  - `mongo_utils/` - MongoDB utilities (MongoIO singleton, document encoding, infinite scroll)
  - `routes/` - Flask route blueprints with factory functions (config, dev-login, metrics, explorer)

- `tests/` - Test suite for all components

## Usage

```python
from api_utils import Config, MongoIO, create_flask_token, create_flask_breadcrumb

# Get config singleton
config = Config.get_instance()
print(config.MONGO_DB_NAME)
print(config.OLLAMA_MODELS)

# Get MongoDB connection singleton
mongo = MongoIO.get_instance()
documents = mongo.get_documents("my_collection")
```

### Infinite scroll (cursor-based pagination)

Use `execute_infinite_scroll_query` for list endpoints with server-side pagination, sorting, and optional name search. It validates parameters (raises `HTTPBadRequest` when invalid), builds the MongoDB filter and sort, runs the query, and returns `{items, limit, has_more, next_cursor}`.

```python
from api_utils import Config, MongoIO
from api_utils.mongo_utils import execute_infinite_scroll_query

mongo = MongoIO.get_instance()
config = Config.get_instance()
collection = mongo.get_collection(config.CONTROL_COLLECTION_NAME)
allowed_sort_fields = ["name", "description", "status", "created.at_time", "saved.at_time"]

result = execute_infinite_scroll_query(
    collection,
    name=request.args.get("name"),
    after_id=request.args.get("after_id"),
    limit=request.args.get("limit", 10, type=int),
    sort_by=request.args.get("sort_by", "name"),
    order=request.args.get("order", "asc"),
    allowed_sort_fields=allowed_sort_fields,
)
# result["items"], result["limit"], result["has_more"], result["next_cursor"]
```

Ensure `handle_route_exceptions` wraps your route so `HTTPBadRequest` is returned as 400.

## Route Registration Pattern

All routes in `api_utils` follow a consistent factory function pattern. This makes route registration declarative and easy to read:

```python
from flask import Flask
from api_utils import (
    create_metric_routes,
    create_explorer_routes,
    create_dev_login_routes,
    create_config_routes
)

app = Flask(__name__)

# Configure Prometheus metrics middleware (exposes /metrics endpoint)
metrics = create_metric_routes(app)

# Register route blueprints
app.register_blueprint(create_explorer_routes(), url_prefix='/docs')
app.register_blueprint(create_dev_login_routes(), url_prefix='/dev-login')
app.register_blueprint(create_config_routes(), url_prefix='/api/config')
```

### Available Route Factories

- **`create_metric_routes(app)`** - Configures Prometheus metrics middleware. **Note:** This is middleware, NOT a blueprint. It wraps the Flask app directly and automatically exposes `/metrics`. Do not use `app.register_blueprint()` with this. Returns the metrics object.
- **`create_explorer_routes(docs_dir=None)`** - Serves static API explorer files (OpenAPI/Swagger docs). Defaults to `docs/` directory. Returns a Flask Blueprint.
- **`create_dev_login_routes()`** - Development JWT token issuance endpoint. Always returns a blueprint; returns 404 when `ENABLE_LOGIN=False` (hides endpoint existence). Returns a Flask Blueprint.
- **`create_config_routes()`** - Configuration endpoint that returns runtime config (requires JWT authentication). Returns a Flask Blueprint.

### Security Note

The `dev-login` endpoint always registers a blueprint, but returns 404 (Not Found) instead of 403 (Forbidden) when disabled. This prevents revealing the endpoint's existence to unauthorized users.

## Demo Server

A demonstration server is included to showcase the utilities and support black-box testing.

### Starting the Server

```bash
# Start the demo server (ENABLE_LOGIN=true is set automatically)
pipenv run dev

# Server will be available at http://localhost:8080
```

### API Explorer

Visit **http://localhost:8080/docs/explorer.html** for an interactive API explorer with:
- Complete endpoint documentation
- Try-it-out functionality for testing
- Request/response examples
- Authentication testing

### Available Endpoints

- `/docs/explorer.html` - Interactive API Explorer (Swagger UI)
- `/docs/openapi.yaml` - OpenAPI specification
- `/dev-login` - Development JWT token issuance (returns 404 if `ENABLE_LOGIN=false`)
- `/api/config` - Configuration endpoint (requires valid JWT token)
- `/metrics` - Prometheus metrics endpoint

### Quick Examples

```bash
# Get a development token
TOKEN=$(curl -s -X POST http://localhost:8080/dev-login \
  -H "Content-Type: application/json" \
  -d '{"subject": "user-123", "roles": ["admin"]}' | jq -r '.access_token')

# Get configuration
curl http://localhost:8080/api/config \
  -H "Authorization: Bearer $TOKEN"

# Get Prometheus metrics
curl http://localhost:8080/metrics
```

### What the Server Demonstrates

- Config singleton initialization
- MongoIO singleton connection
- Flask route registration with factory pattern
- Prometheus metrics integration
- JWT token authentication and authorization
- Interactive API documentation
- Graceful shutdown handling

## Package Installation

**Installation from GitHub (HTTPS with Token):**

All installations use HTTPS with GitHub Personal Access Tokens (PATs).

**Normal Installation:**
```bash
# Configure git to use your GitHub token (one-time setup):
git config --global url."https://<YOUR_TOKEN>@github.com/".insteadOf "https://github.com/"

# Then install normally
pipenv install git+https://github.com/agile-crafts-people/api_utils.git
```

**Development Installation (Editable Mode):**
```bash
pipenv install -e git+https://github.com/agile-crafts-people/api_utils.git#egg=api-utils
```

Use editable mode when you're **simultaneously working on both**:
- The consuming project (e.g., evaluator_api)
- AND the `api_utils` package itself

Editable mode links to your local `api_utils` clone, so changes to `api_utils` are immediately available in the consuming project without reinstalling.

**Alternative: Credential Helper (Recommended)**
```bash
# Store credentials securely
git config --global credential.helper store
# On first git operation, enter your username and token as password
```

## Standards Compliance

This package implements the Creator Dashboard API standards:
- ✅ Config singleton for configuration management
- ✅ Logging initialized by Config singleton
- ✅ Prometheus metrics endpoint for monitoring
- ✅ Config endpoint for runtime configuration
- ✅ Standard pipenv scripts (build, dev, test)
- ✅ server.py as standard API entry point
- ✅ JWT authentication with signature verification
- ✅ Security-first design with fail-fast validation
- ✅ **Architecture alignment** - Port numbers and collection names match `architecture.yaml`

### Architecture Integration

All port numbers and collection names are defined to match the [Creator Dashboard architecture](https://github.com/agile-crafts-people/CreatorDashboard/blob/main/Specifications/architecture.yaml):

**Ports by Domain:**
- Common Code: 8080
- MongoDB: 8180-8181
- Runbook: 8083-8084
- Templates: 8081-8082
- Profile: 8182-8183
- Evaluator: 8184-8185
- Dashboard: 8186-8187
- Classifier: 8188-8189

**Collection Names by Domain:**
- System: DatabaseEnumerators, CollectionVersions
- Template: Control, Create, Consume
- Profile: Profile, Platform, User
- Evaluator: TestRun, TestData, Grade
- Dashboard: Dashboard, Post, Comment
- Classifier: Sentiment, Ratio

See [ARCHITECTURE_ALIGNMENT.md](./ARCHITECTURE_ALIGNMENT.md) for complete details and migration notes.

Note: The standards specify FastAPI, but this utility package uses Flask from familiarity. The package structure supports migration to FastAPI in the future. 

## Security

api_utils implements security best practices including:
- **JWT signature verification** - Tokens are validated with proper signature verification when `JWT_SECRET` is configured
- **Fail-fast validation** - Application will not start if `JWT_SECRET` uses the default insecure value
- **Secret masking** - Configuration secrets are masked in logs and API responses
- **Development mode protection** - `/dev-login` endpoint is disabled by default

### Production Security Checklist

Before deploying to production, ensure:
- [ ] `JWT_SECRET` is set to a strong, randomly generated value
- [ ] `ENABLE_LOGIN` is set to `false` (default)
- [ ] MongoDB connection uses authentication and encryption
- [ ] HTTPS/TLS is configured
- [ ] Monitoring and logging are enabled

**See [SECURITY.md](./SECURITY.md) for complete security documentation.**

# Future Roadmap

api_utils is the official standards-compliant Python package used by all Creator Dashboard python projects. It is currently installed via HTTPS with GitHub Personal Access Tokens (PATs). 

✅ **Completed:** Identity Testing endpoint (`/dev-login`) to issue JWTs for local development and testing.

In a future release, we will implement automated validation tests on every PR Merged to Main ensuring changes to api_utils don’t silently break consumers.

Once a number of production deployed consumers exist, version stability becomes important so they can pin known-good releases instead of tracking a moving branch. We will introduce semantic versioning via Git tags and expose the version in the package, allowing consumers to pin exact versions.

As usage grows, build performance and reproducibility start to matter, especially in CI and container builds. We will add a release workflow that builds wheels and source distributions on tag pushes, producing immutable binary artifacts.

After versioned artifacts exist, consumer environments should become deterministic rather than dependency-resolution-dependent. We will adopt lock files (poetry.lock or compiled requirements.txt) in consuming repos, ensuring reproducible installs across machines and CI.

Once funding or organizational maturity allows, infrastructure improvements can replace the Git-based distribution without changing the package itself.
	•	Stand up a private JFrog Artifactory PyPI repository, providing centralized, permissioned package hosting.
	•	Migrate consumers from git+https installs to the private PyPI index by changing only index configuration, preserving package names and versions.
	•	Enable artifact promotion, vulnerability scanning, and access controls (e.g., Xray, repo permissions).

As the ecosystem grows, the package itself may need clearer guarantees.
	•	Formalize API stability rules, deprecation policies, and backward-compatibility contracts.