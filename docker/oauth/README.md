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
