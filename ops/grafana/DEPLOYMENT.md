# Production activation — 2026-11-21

Grafana Alloy v1.22.0 is active on the existing NodeJS droplet and `ngx-net`.
No new droplet or published collector port was added. The user created the
stack-scoped `my-monitoring-token` with only `logs:write` and `metrics:write`,
then entered its value through a hidden host terminal prompt. The credential
exists only in `/etc/ngx-workshop/observability/grafana.env`, root:root mode 0600.
Never include its contents in diagnostic output or Git.

## Verified evidence

- All thirteen deployed NestJS containers returned HTTP 200 with Terminus
  `status: ok` / heartbeat `up`, and Docker reported each `healthy`.
- Every service container uses json-file rotation `max-size=10m`, `max-file=3`.
- Grafana displayed all thirteen heartbeat series as UP and response-time series.
- Native JSON startup/access logs arrived in Loki. Harmless GET requests to an
  unmatched monitoring path generated fresh access logs that were visible in the
  dashboard after collector recreation, confirming collection resumed.
- Alloy remained running with zero restarts after final recreation; its startup
  logs contained no warnings/errors and no host ports were bound.
- Compose mount validation and a fresh disposable volume write check passed on
  the host with all capabilities dropped. CI also checks the parsed tmpfs and
  nocopy settings without resolving the production credential file.

[Service health and logs dashboard](https://ivorytoffee195.grafana.net/d/ngx-workshop-services/)
uses the stack's existing `grafanacloud-ivorytoffee195-prom` and
`grafanacloud-ivorytoffee195-logs` data sources; refresh is 30 seconds.
Heartbeat proves process liveness, not database or upstream readiness.
The error panel has no data when no error/fatal records exist in its five-minute
window. Notifications/contact points have not been configured.

| Container | Heartbeat / Docker health |
| --- | --- |
| ngx-auth-service | UP / healthy |
| ngx-mfe-orchestrator | UP / healthy |
| ngx-workshop-bff | UP / healthy |
| seed-service-nestjs | UP / healthy |
| service-user-metadata | UP / healthy |
| service-nestjs-assessment-test | UP / healthy |
| service-navigational-list | UP / healthy |
| document | UP / healthy |
| backstage | UP / healthy |
| coding-labs | UP / healthy |
| service-uploader | UP / healthy |
| service-mcp-gateway | UP / healthy |
| service-ai-publisher | UP / healthy |

AI Chat has logging/heartbeat source support but is not deployed or probed.

## Rollout corrections

The global auth-client guards in uploader, navigation and orchestrator require
explicit `@Auth(AuthType.None)` on the heartbeat handler. Regression tests now
exercise the actual authentication/role guards and reject a protected route.
The BFF's legacy plain-text `/health` handler was removed to leave one Terminus
route. All four corrected deployments succeeded.

The gateway deployment readiness probe called `wget`, absent from the current
backhaul image. It now uses the installed `curl`, retaining the same proxy source,
exact ingress headers, timeout, metadata check and rollback behavior. Its six
deployment tests and the live trusted-proxy check passed; the corrected
[production workflow](https://github.com/Ngx-Workshop/service-mcp-gateway/actions/runs/44928214858)
succeeded.

The unrelated edge Nginx validation remains blocked by its pre-existing unavailable
image reference. No edge image/config change was required for this activation.
