# sales_agent_HW

Testing for setting up a GitHub repository for an agent.

Sales Agent Infrastructure Assignment: FastAPI, frontend, MCP, and Docker.

Expose the existing LangGraph sales agent through FastAPI, add a simple
frontend, deploy the services with Docker, and test the complete flow.

## Project structure

- `backend/`: FastAPI API and LangGraph agent integration.
- `frontend/`: Simple interface for submitting sales analysis requests.
- `mcp_service/`: MCP service that supplies actual sales data.
- `tests/`: Backend checks, MCP/live verification scripts, and Docker browser test results.

The backend, frontend, and MCP service each have their own Dockerfile.
Docker Compose runs all three services together. The frontend uses plain
HTML/CSS/JavaScript served by Nginx, which proxies analysis requests to FastAPI.

## Run the MCP service locally

From the project root, using Python 3.13:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r mcp_service/requirements.txt
.\.venv\Scripts\python.exe mcp_service/sales_mcp_server.py
```

The MCP endpoint is `http://127.0.0.1:8001/mcp`. This service needs no API
key. It exposes `get_sales(region, period)` for Singapore in `2026-Q1`,
`2026-Q2`, and `2026-Q3`, and returns an error object for unknown inputs.
It uses MCP SDK `2.3.0`, matching the SDK verified during extraction.

`MCP_HOST` and `MCP_PORT` can override the listening address and port.
The later Docker configuration will set `MCP_HOST=0.0.0.0` so the backend
container can connect to the service.

## Configuration

`.env.example` contains configuration names and no credentials. When runtime
setup is ready, copy it to `.env` and supply your own API key and model name.
Git and Docker ignore local environment files. Original notebooks are also
excluded because they may contain credentials or saved outputs.
Settings in the project's `.env` take priority over existing environment
variables. Without that file, the backend uses its process environment.

## Run the backend locally

Install its dependencies in the project virtual environment:

```powershell
.\.venv\Scripts\python.exe -m pip install -r backend/requirements.txt
```

Create `.env` from `.env.example`, enter your own key and an accessible model,
and change `MCP_SERVER_URL` to `http://127.0.0.1:8001/mcp` for local execution.
Start the MCP service in one terminal and the backend in another:

```powershell
.\.venv\Scripts\python.exe -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

Open `http://127.0.0.1:8000/docs` for interactive API documentation.
`GET /health` reports whether model settings are configured; it does not
verify connectivity or API key validity. `POST /api/analyze` accepts:

```json
{"prompt": "Compare Singapore's sales for 2026-Q2 with target and calculate the percentage variance."}
```

The response has an `answer` field containing the agent's text. Each request
starts a new conversation. Requests have a 90-second timeout and the graph
retains the notebook's recursion limit of 10.

Run credential-free backend checks with:

```powershell
.\.venv\Scripts\python.exe tests/check_backend.py
```

These checks use a scripted model and do not validate a live OpenAI call.
The MCP HTTP integration check is `python tests/check_mcp.py`.

## Preview the frontend locally

With the backend running at `http://127.0.0.1:8000`, run from the project root:

```powershell
python frontend/dev_server.py
```

Open `http://127.0.0.1:8080`. The preview server serves only the public HTML,
CSS, and JavaScript assets and forwards `/api/analyze` to the backend. It
does not read API credentials. Stop it with Ctrl+C. This is an optional
development preview; stop it before starting the Docker frontend on port 8080.

The interface includes a question field, quarter examples, loading feedback,
analysis text, and retryable errors. Answers are displayed as plain text,
including any Markdown notation supplied by the model.

## Run with Docker Compose

Requires Docker Engine with Docker Compose and Linux containers (for example,
Docker Desktop on Windows). Run these commands from the project root after
providing `OPENAI_API_KEY` and `OPENAI_MODEL` in the local `.env` file:

```powershell
docker compose config --quiet
docker compose up --build -d
docker compose ps
```

Open the frontend at `http://127.0.0.1:8080`. It stays available while its
Docker container and Docker Engine are running; no Python preview server is
needed. Nginx forwards `/api/analyze` to `http://backend:8000/api/analyze` on
the Compose network. Its proxy timeout is 95 seconds, above the backend's
90-second request limit. The frontend receives no API credentials.

The API is also available at `http://127.0.0.1:8000`, with documentation at `/docs`.
The backend listens on port 8000 inside its container; the host port is bound
to localhost. MCP is reachable only inside the Compose network at
`http://mcp:8001/mcp`, without a published host port.

Compose loads `.env` as runtime environment settings for the backend. Its
explicit `MCP_SERVER_URL` overrides the local address from `.env`, so no
change to your local Python configuration is required. The MCP container
does not receive the backend's credentials. None of the images copies `.env`.
The backend and MCP images run as a non-root user; the frontend uses the
official Nginx image's default process configuration.

The MCP health check verifies its TCP listener; the backend health check
verifies `/health`. The frontend checks its own Nginx `/health` endpoint.
These checks do not perform paid OpenAI requests or
prove the complete analysis flow works.

To stop and remove these containers and their Compose network:

```powershell
docker compose down
```

Backend and MCP images have been built and both services verified healthy with Docker
Compose on Windows using Linux containers. A live request to the containerized
API returned HTTP 200 for Singapore `2026-Q2`, with actual `200`, target `300`,
and variance `-33.33%`. This verifies the backend/model/MCP flow.
The frontend image has also been built and deployed healthy. Nginx
configuration validation, HTML/CSS/JavaScript asset requests, and forwarding
of invalid input to FastAPI (HTTP 422) have passed through port 8080.

The complete Docker deployment has passed browser end-to-end checks for Q2
analysis, missing Q4 data, loading behavior, and blank prompt validation.
See [the test results and repeat instructions](tests/E2E_RESULTS.md).

## Agent behavior to preserve

1. Retrieve actual sales through MCP.
2. Retrieve the target with a local agent tool.
3. Calculate percentage variance: `(actual - target) / target * 100`.
4. Return the agent's analysis to the frontend through FastAPI.

Reference case: Singapore, `2026-Q2` has actual sales of `200`, a target of
`300`, and percentage variance of `-33.33%`.
