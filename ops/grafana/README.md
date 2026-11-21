# NGX Workshop service observability

The NodeJS Docker host runs one Grafana Alloy collector on the existing `ngx-net`.
No new droplet, inbound port, frontend logger dependency or application-held Grafana
credential is required. Logs use native NestJS 11 `ConsoleLogger({json:true})` and
contextual `Logger` calls. Alloy ships to the `ivorytoffee195` Grafana Cloud stack.

## Heartbeats

Each service exposes anonymous `GET /health` (and automatic HEAD) on its existing
port. The response is Terminus `status: ok` with a `heartbeat: up` indicator and
`Cache-Control: no-store`. It only establishes liveness, not MongoDB or upstream
readiness. Docker health checks and Alloy HTTP probes use this endpoint. There
are thirteen production targets; AI chat has source support but is not deployed.
Other service authentication/ingress checks remain in force. The gateway exempts
only the exact read-only heartbeat from its proxy-envelope requirement.

## Prepare and activate

Copy this directory to `/opt/ngx-observability` on the NodeJS host. Prepare
`/etc/ngx-workshop/observability/grafana.env` as root-owned 0600, using the example
and a token with **only `logs:write` and `metrics:write` for stack ivorytoffee195**.
Creating the access policy/token is a separate account authorization step. Never
commit or transfer the real credential through Actions or application environments.

```sh
cd /opt/ngx-observability
docker compose -f compose.yml run --rm --no-deps alloy validate /etc/alloy/config.alloy
docker compose -f compose.yml up -d
```

The collector needs Docker API access to discover/read logs. A read-only socket
mount does not make the Docker API read-only; this is a trusted host agent. It has
no published port, dropped capabilities, a read-only root, 256 MiB memory and
half a CPU. Logs are buffered by Docker with 10 MiB × 3 files per NestJS container.
Alloy stores log offsets and a heartbeat metric WAL in `alloy-data`; WAL history is
bounded to two hours. No system journals, host files or unrelated container logs
are exported. Service names, environment and severity are low-cardinality labels;
request IDs and contexts remain JSON fields.

Import `dashboard.json` in Grafana, selecting this stack's Loki and Prometheus
data sources. It provides service heartbeat tiles, response times, error counts
and searchable NestJS logs. No alert contact points or notifications are created.
Useful queries:

```logql
{job="ngx-workshop/nestjs",service_name="service-mcp-gateway"} | json
```

```promql
probe_success{environment="production"}
```

Check that all thirteen probes are `1`, the log query returns current JSON records,
and Alloy has no remote-write authorization errors. A running collector is not
proof of Grafana receipt. Pending account authorization means no ingestion yet.

## Local verification

Alloy v1.22.0 validation passed using the checksum-verified official Darwin arm64
binary and a dummy token (no ingestion). CI validates the Docker deployment config
with dummy credentials. NestJS HTTP tests cover JSON shape, route-template logging,
input exclusion, anonymous heartbeat and business-route authorization. Deployment
and Grafana ingestion evidence should be recorded after activation.
