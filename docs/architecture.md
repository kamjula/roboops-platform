# Architecture

RoboOps uses a React/Vite frontend, a FastAPI service, PostgreSQL persistence,
and Redpanda/Kafka telemetry transport. The HTTP service exposes Prometheus
metrics at `/metrics` and returns `X-Request-ID` on every handled response.
Caller-supplied request IDs are accepted only when they match a bounded safe
character set; otherwise, the service generates a UUID. Access logs carry a
JSON payload with the same request ID for correlation. CORS responses expose
the header so browser clients can include it in support and incident reports.

HTTP metrics use route templates such as `/api/v1/robots/{robot_id}` rather
than raw URLs. This avoids unbounded metric-cardinality growth from UUIDs or
other path parameters. Unknown routes share the `__unmatched__` label.

The current metrics endpoint is intentionally unauthenticated for scraper
compatibility. It exposes framework/process and aggregate route telemetry, not
request bodies, credentials, robot identifiers, or telemetry values. Network
access control and a dedicated Prometheus deployment remain hosting concerns;
the repository does not claim that monitoring is deployed in production.
