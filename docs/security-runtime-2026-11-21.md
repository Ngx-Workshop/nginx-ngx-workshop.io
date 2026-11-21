# Production runtime security rollout — 2026-11-21

Container rollout completed and independently verified at approximately 13:33 UTC.
The user authorized updates and deployment; production had no live users and downtime was acceptable.

## Result

| Component | Before | After | Verified scope |
| --- | --- | --- | --- |
| 12 Node services | 22.23.3 | 22.23.5 | Running version, startup port, stable process, runtime settings |
| coding-labs | 22.23.4 | 22.23.5 | Same checks plus isolated Docker runner |
| Public Nginx edge | 1.30.5 | 1.30.7 | nginx -t, unchanged configuration, public HTTP |
| Private OAuth backhaul | 1.30.5 | 1.30.7 | nginx -t, private addresses/settings preserved, public OAuth/MCP routing |

All 15 production containers were running with zero restarts at final verification.
No inference of actual server compromise was made; this rollout addresses published runtime vulnerabilities.

## Image identities and method

Official images were pulled and their manifest digests inspected on the Docker hosts:

- Node: `node:22.23.5-alpine@sha256:1314fb30ec37592d5845e5a160d522c0e680972aa534549940b8d73bde88481a`.
- Nginx: `nginx:1.30.7@sha256:7fadc6c0ff97965adbddf28027d934b111fc0221a554315dc274712f3fba24d3`.

The application's host source folders did not consistently reflect newer repository build configuration.
The immediate Node rollout therefore used multi-stage runtime rebases: exact deployed application files were copied onto the official patched base. Every candidate's dist manifest matched the deployed application's dist files byte for byte. Auth's native bcrypt binding was tested on the new image. Both bases are within Alpine 3.24; no Node major upgrade or API change was introduced. Coding-labs retained its Docker CLI.

The public edge was built from the patched Dockerfile after confirming the host's nginx.conf exactly matched the live file. The private backhaul was replaced separately using its existing mounted configuration and certificate. The edge workflow alone does not deploy the backhaul.

Replacement containers preserve the inspected environment, commands, users, mounts, security flags, restart policies, port bindings and application-network IP addresses. The intentional differences are the runtime image, runtime version metadata, patch label and the pinned RUNNER_IMAGE on coding-labs. The backhaul was reloaded after service replacement.

The isolated runner was verified from inside coding-labs using the pinned image with no network, read-only root, dropped capabilities, memory and PID limits. The host runner setting was updated to survive later container recreation.

## Verification

- All 13 Node candidates: version 22.23.5 and unchanged deployed dist manifest.
- Auth: native bcrypt hash succeeds on the new runtime.
- Disposable replacement: successful HTTP service replacement; failed initial disposable test automatically restored its previous container. Temporary test containers were removed afterward.
- Production: 13 Node versions, startup ports and stable processes; both Nginx syntax checks; zero restarts at final audit.
- Application host audit: users, entrypoints, commands, working directories, runtime environment, mounts, security settings, bindings, restart policies and application-network IPs preserved.
- Edge audit: live/source nginx.conf identical, security settings and mounts preserved.
- Local coding-lab runner tests: 4 passing; source whitespace and Python syntax checks pass.

Public HTTPS checks with normal certificate verification:

| Request | Expected and actual |
| --- | --- |
| GET beta.ngx-workshop.io/ | 200 |
| GET admin.ngx-workshop.io/ | 200 |
| GET auth.ngx-workshop.io/ | 200 |
| GET beta.ngx-workshop.io/api/documents/navigation/sections | 200 |
| GET mcp.ngx-workshop.io/.well-known/oauth-protected-resource/mcp | 200; resource identity checked |
| GET auth.ngx-workshop.io/.well-known/oauth-authorization-server | 200 |
| GET auth.ngx-workshop.io/api/auth/validate-access-token | 200 |
| Unauthenticated POST mcp.ngx-workshop.io/mcp | 401 |
| Unauthenticated POST admin.ngx-workshop.io/api/publisher/tools with allowed Origin | 401 |
| Allowed-Origin publishing OPTIONS preflight | 204 |

These checks do not establish signed-in Google/GitHub authorization-code flows, authenticated authoring, or full end-user journeys. No paid generation, workshop mutation, database migration or credential rotation was performed. Full CI suites were not run for this coordinated runtime deployment. Source commits use [skip ci] to avoid a second automatic rollout; later normal builds consume the patched pins.

## Source changes

Dockerfiles and configured CI Node versions were patched in all 13 service repositories. Coding-lab runner defaults, example environment and deployment pull reference use the pinned patched image. The seed is included because its service is running in production. Unrelated service-auth sign-out edits were preserved and excluded from published commits.

| Repository | Published main commit |
| --- | --- |
| service-auth | [70e9d64f](https://github.com/Ngx-Workshop/service-auth/commit/70e9d64f6ef88a29907ed010445b3a08f3f509ec) |
| service-mcp-gateway | [c9b2f5d5](https://github.com/Ngx-Workshop/service-mcp-gateway/commit/c9b2f5d51d215ce110ff1aeaa0fb3a12bcd0d1d6) |
| service-ai-publisher | [2849556b](https://github.com/Ngx-Workshop/service-ai-publisher/commit/2849556bc01396f39514d997752db332d66b40d3) |
| service-coding-labs | [a4780951](https://github.com/Ngx-Workshop/service-coding-labs/commit/a47809510be4fe2c55985e9e78399a434829f1a3) |
| service-user-metadata | [3b174c98](https://github.com/Ngx-Workshop/service-user-metadata/commit/3b174c988a3c2a00ea96108e03743a5ae0d297b5) |
| service-mfe-orchestrator | [242817d5](https://github.com/Ngx-Workshop/service-mfe-orchestrator/commit/242817d54af48b099f95069a2286121c5e0399bf) |
| service-assessment-test | [7ebc1648](https://github.com/Ngx-Workshop/service-assessment-test/commit/7ebc16488b66d9963b9047e62833d12631e87d67) |
| service-document | [33e9bdb1](https://github.com/Ngx-Workshop/service-document/commit/33e9bdb11bf13e85d3ab871e79c56192feb58fe0) |
| service-uploader | [8d902136](https://github.com/Ngx-Workshop/service-uploader/commit/8d902136432ccbcb1a05fd854c74ee7b941d46b7) |
| seed-service-nestjs | [7b3476e8](https://github.com/Ngx-Workshop/seed-service-nestjs/commit/7b3476e8ef43d819046277718cdaf9ddb6c0d8df) |
| service-bff-ngx-workshop | [8f67c646](https://github.com/Ngx-Workshop/service-bff-ngx-workshop/commit/8f67c646bc4ef72258693bdbb4ab140b1eb4bba8) |
| service-backstage | [6c679a5d](https://github.com/Ngx-Workshop/service-backstage/commit/6c679a5d5bc9d0e75291b244078a15877979882a) |
| service-navigational-list | [48f7b088](https://github.com/Ngx-Workshop/service-navigational-list/commit/48f7b0884353dc12bcd2ebe73231cf9068f8a84d) |

The Nginx repository also updates the edge Dockerfile, CI backhaul validation image, backhaul reference documentation and reusable rollout helpers. This record is part of that Nginx security commit.

At initial rollout completion, working-tree edits mirrored the published security changes and local Git HEADs had not yet advanced. The Git synchronization follow-up below resolves this.

## Recovery state

Both hosts retain a private root-owned release directory:
`/opt/ngx-releases/security-20261121`.

- `production/*.before.json`: original Docker inspection, including sensitive runtime configuration; do not publish or transfer these files.
- `production/*.replacement.json`: replacement configuration, also private.
- Previous production containers: `<name>.before-security-20261121`, stopped with restart disabled.
- Old images remain referenced by rollback containers; no production volumes or images were pruned.
- Application host: candidate Dockerfiles/build logs, candidates.json, rollout.log, verification-public.json and success markers.
- Edge host: original Dockerfile, unchanged live configuration source and public-http-verification.json.
- Original host Dockerfiles and the coding-labs environment were backed up privately before patching.

Rollback requires stopping/disconnecting the replacement, restoring the old container's original name and network endpoints from its snapshot, restoring its saved restart policy, starting it, and repeating the HTTP checks. Reload Nginx after restoring service endpoints. Keep publisher single-writer semantics and its existing receipt volume. Do not start a rollback container alongside its replacement.

## Host operating-system follow-up

The hosts started on Ubuntu 24.10 (application) and 25.04 (edge), both end of life. Container patches do not update the host kernel, OpenSSH, Docker daemon or Ubuntu packages. The subsequently authorized OS maintenance, recovery snapshots and validation are tracked in [Ubuntu LTS maintenance](ubuntu-lts-upgrade-2026-11-21.md).

Official references:

- https://nginx.org/en/security_advisories.html
- https://nodejs.org/en/blog/vulnerability/november-2026-security-releases/
- https://wiki.ubuntu.com/Releases


## Git synchronization and Ubuntu preflight follow-up — 2026-11-21

All 14 local main checkouts were fetched and fast-forwarded to the published security commits. Before updating HEAD/index, every file changed by the remote commit was compared byte for byte against the local working file. Working-file SHA-256 manifests were checked afterward. No working-tree files changed during synchronization. Thirteen repositories are clean. service-auth retains only the pre-existing authentication.controller.ts change and untracked sign-out.spec.ts. Private sync checkpoints are in /tmp/ngx-git-sync-20261121 on the Mac; they are temporary recovery aids, not a durable release artifact.

At the initial preflight, DigitalOcean browser management access became available. The application Droplet is 604241659 and the edge Droplet is 604241182, both in NYC1. Their private addresses are 10.116.0.4 and 10.116.0.3 respectively. No current backups/snapshots were listed at that preflight; automated backups were disabled on both. The later approved snapshot creation is recorded in the Ubuntu maintenance document.

Both hosts pass dpkg --audit with no held packages. Both have screen and tmux, adequate root/boot free space and an installed release upgrader. Read-only release checks advertise Ubuntu 26.04.1 LTS. The upgrade path still needs validation before executing a release transition; do not infer that the advertisement authorizes skipping interim releases. Existing failed units were observed: logrotate on the edge; cloud-final, cloud-init-main and droplet-agent-install-retry on the application host. These findings are recorded as pre-existing, not caused by the container rollout.

The user subsequently approved the additional snapshot storage cost. Both offline snapshots completed (edge 8.35 GB, application 53.05 GB; approximately $3.684/month combined while retained). Ubuntu maintenance is complete: both hosts run 26.04.1 LTS / kernel 7.0.0-44 with Docker 29.10.0. All 15 production containers were restored, their configuration audited, and all ten public checks plus the coding-lab sandbox smoke passed. See the linked maintenance record for details and validation limits. Existing approval covers the OS upgrades and downtime.
