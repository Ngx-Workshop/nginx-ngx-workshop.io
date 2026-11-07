# OAuth backhaul and edge

The edge validates TLS to the application host using the private service CA
mounted through the existing /etc/letsencrypt read-only mount. It replaces
forwarded authority/protocol/client headers and disables access logs for OAuth
and MCP so authorization query strings are never written to logs.

The nonroot application proxy uses pinned nginx digest
`sha256:0985e772fb9f729e6fa0980da05fca5d9c468e870eed43071545afa9d2e27d94`,
fixed unused ngx-net address 172.18.0.240, private 10.116.0.4:3443 listener,
read-only config/certificate mounts, tmpfs, dropped capabilities, and exact
edge-private-IP allowlisting. Runtime auth/gateway ports have no public bindings.

Validate staged edge config with the existing certificate/static mounts before
recreation. Retain the previous image/container and configuration for rollback.
CA and private certificates are operator-managed; never place private keys in Git.

## Administrator workshop publishing

Native HTTPS now routes admin.ngx-workshop.io/api/publisher/tools through the existing verified TLS backhaul with Host mcp.ngx-workshop.io. Other hosts cannot use this facade. The MCP hostname additionally exposes /mcp/publishing for authenticated platform administrators. AI publisher validates every credential and admin role; read-only catalog OAuth does not authorize publishing. Both hops allow 8 MiB and 180-second requests for publishing while existing catalog limits stay intact. Deploy both nginx configuration changes with the gateway/MFE release. Configuration syntax was checked with temporary local certificates; no production reload occurred.

## Direct AI publisher routing — 2026-11-06

Source routing now sends /publisher/tools and /mcp/publishing from the verified
private backhaul directly to service-ai-publisher:3014. Catalog /mcp and metadata
still reach service-mcp-gateway:3011. The edge preserves its exact administrator-only
/api/publisher/tools route, /api stripping, normalized proxy headers, certificate
verification, 8 MiB limit and 180-second timeout. Publisher validates credentials
and administrator role. The obsolete /api/ai-publisher seed route now returns 410;
no publisher host port needs to be exposed.

Deploy the backhaul configuration on the application host as well as the edge
configuration. The existing edge workflow deploys docker/nginx.conf only; it does
not install docker/oauth/backhaul.conf on the application host. Back up the live
mounted backhaul file, update its existing inode, run nginx -t in ngx-oauth-backhaul,
then reload, restoring the backup on failure. Validate public administrator facade
401/allowed-Origin preflight and catalog metadata before removing gateway
compatibility endpoints. Frontend uses publisher contracts and keeps its browser URL.
These local source changes do not perform deployment/reload or paid generation.

## Production deployment — 2026-11-06

User authorized update and deployment. Source commits were pushed to main:
- nginx-ngx-workshop.io: 2f4dea273b7ad91993d886aa8aacdcf44f518fb3.
- mfe-user-journey-admin-ai-publisher: 574979267e3824da9965b98073ffd1043c48c41c.

The application-host backhaul was backed up under
/etc/ngx-workshop/releases/direct-publisher-20261106T231435Z. The reviewed source
matched the expected live baseline; its mounted inode was preserved, nginx -t
passed and reload succeeded. The edge configuration and previous publisher assets
were backed up under /opt/ngx-releases/direct-publisher-20261106T231457Z on the edge.
No service settings, model credentials, receipt storage or content were changed.

Nginx validation/deployment run 42310554724 succeeded. Frontend deployment run
42310556622 and independent validation run 42310556627 succeeded, including clean
install, architecture, ChromeHeadless tests, strict app types and production build.
Both live Nginx configurations hash-match the committed source.

Final public checks:
- Catalog metadata GET 200; unauthenticated catalog MCP POST 401.
- Agent publishing POST 401.
- Admin browser facade POST with allowed Origin/no credentials 401.
- Allowed-Origin browser preflight 204.
- Facade on beta host 403; untrusted Origin on admin host 403.
- Retired /api/ai-publisher GET 410.
- Public federation remoteEntry.js hash matches the deployed file. Its referenced
  2181.eee6ef2fa5d7c78e.js chunk serves successfully and contains publisher contract
  metadata (ngx-workshop-publisher).

The browser URL remains /api/publisher/tools, now routed directly by the TLS
backhaul to service-ai-publisher:3014. Catalog routing remains on the gateway.
No paid provider call, signed-in account flow, workshop mutation or receipt write
was used for verification. Rollback assets/configurations remain preserved.

Deployment links:
- https://github.com/Ngx-Workshop/nginx-ngx-workshop.io/actions/runs/42310554724
- https://github.com/Ngx-Workshop/mfe-user-journey-admin-ai-publisher/actions/runs/42310556622
- https://github.com/Ngx-Workshop/mfe-user-journey-admin-ai-publisher/actions/runs/42310556627

These deployment evidence additions are recorded locally after the functional source
commits were deployed; no second docs-only deployment was triggered.
