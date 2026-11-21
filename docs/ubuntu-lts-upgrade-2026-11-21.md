# Ubuntu LTS maintenance — 2026-11-21

Status: completed. Both production hosts booted into Ubuntu 26.04.1 LTS and their 15 production containers were restored and verified. The user authorized upgrades, downtime, local Git synchronization and the additional storage cost for two recovery snapshots.

## Result

| Role | Droplet | Public / private IP | OS before → after | Booted kernel | Docker Engine | Containers |
| --- | --- | --- | --- | --- | --- | --- |
| Edge | 604241182 nginx-s-1vcpu-2gb-70gb-intel-nyc1 | 167.172.154.106 / 10.116.0.3 | 25.04 → 26.04.1 LTS | 7.0.0-44-generic | 29.10.0 | 1 running |
| Application | 604241659 nodejs-s-2vcpu-8gb-160gb-intel-nyc1 | 24.144.98.154 / 10.116.0.4 | 24.10 → 26.04.1 LTS | 7.0.0-44-generic | 29.10.0 | 14 running |

All 13 Node services still run v22.23.5. Both edge and private backhaul Nginx containers still run 1.30.7. The OS maintenance reused the same container IDs, images and application contents from the preceding [runtime security deployment](security-runtime-2026-11-21.md).

MongoDB remains on its separate Ubuntu 24.04 Droplet and was outside this upgrade scope. No additional Droplets or paid services were created.

## Recovery snapshots

Both hosts' production containers were gracefully stopped, filesystems synced and hosts powered off before DigitalOcean created these snapshots. Both completed before OS package changes, and both hosts were then powered on for maintenance.

| Snapshot | Size |
| --- | --- |
| pre-ubuntu-lts-nginx-20261121 | 8.35 GB |
| pre-ubuntu-lts-nodejs-20261121 | 53.05 GB |

DigitalOcean displayed $0.06/GB/month. The additional 61.40 GB costs approximately **$3.684/month while retained**, subject to provider usage billing. The snapshot names identify the recovery images; numeric image IDs have not been inspected. Existing older account snapshots were not changed.

Root-only checkpoints on each host remain at `/opt/ngx-releases/ubuntu-lts-20261121`:

- `running-containers.txt`: exact production names to restore; excludes previous runtime rollback containers.
- `containers.before.json`, `containers.after.json`: private Docker inspections containing sensitive configuration. Do not publish or transfer them.
- `host-configuration.before.tar.gz`: host configuration, credentials, certificates, SSH/netplan/firewall settings and cron checkpoint.
- OS, kernel and package inventories before/after; original Ubuntu source file; persistent screen logs, baseline/Docker update logs and verification reports.

Previous runtime rollback containers remain stopped with restart disabled; their referenced images and application volumes were retained. Do not start them alongside their replacements. Provider snapshots support recovery of each host's pre-OS-upgrade disk state. Restoring a snapshot rolls back subsequent local disk changes and requires repeating health checks.

## Upgrade execution

1. Verified clean dpkg audits, no held packages, adequate root/boot space, cgroup v2, SSH and persistent screen availability. Captured private checkpoints and completed the offline snapshots.
2. Fully updated each starting release with conffile preservation. Edge: 55 baseline updates; application: 47. Both finished with clean audits, zero remaining packages and no baseline reboot required.
3. Upgraded each host to 25.10 with Canonical's signed Questing upgrader. Its verified configuration explicitly accepts `From=noble,oracular,plucky` and `To=questing`, permitting the application host's accepted 24.10 → 25.10 transition without a forced source-release override. Both rebooted successfully into 6.17.0-41-generic and passed intermediate audits.
4. Used normal `do-release-upgrade --frontend=DistUpgradeViewText` for 25.10 → 26.04.1 LTS. Reviewed package/removal plans and obsolete cleanup lists; Docker and application data were retained. Both rebooted into 7.0.0-44-generic.
5. Configured Docker's official signed `resolute` repository and reviewed its six-package update before applying it. Both now use Engine/CLI/rootless extras 29.10.0, containerd.io 2.4.2, Buildx 0.39.1 and Compose 5.8.0. Docker's public signing-key fingerprint is `9DC8 5822 9FC7 DD38 854A E2D8 8D81 803C 0EBF CD88`.
6. Restored exactly the saved production container names, validated host/container settings, repeated runtime and public-service checks, and set future release prompting to `Prompt=lts`.

The application starting release required signed `old-releases.ubuntu.com` sources. The official upgrader selected normal mirrors for Questing. Edge Plucky packages were available from normal official archive/security mirrors. Final Ubuntu sources on both hosts use official HTTPS archive/security endpoints and only Resolute suites. No signature/TLS checks were disabled, and no development-release option was used.

Release work ran inside persistent screen sessions with separate logs for interim and LTS transitions. Hosts were quiesced during upgrades; independent application baseline/interim work overlapped the edge's final installation after both recovery snapshots had completed.

## Validation

| Check | Result |
| --- | --- |
| Booted OS/kernel on both hosts | Ubuntu 26.04.1 LTS / 7.0.0-44-generic |
| dpkg audit, remaining package upgrades | Clean; zero pending on both |
| Failed systemd units | Zero on both |
| SSH syntax, root key access and original public/VPC addresses | Passed; addresses unchanged |
| UFW, Docker startup and SSH socket activation | Original firewall rules active; startup enabled |
| Docker storage/cgroups | Existing overlay2 retained; cgroup v2 |
| Automatic Ubuntu security updates | apt-daily and apt-daily-upgrade timers enabled; unattended updates enabled |
| Temporary upgrader SSH listener | No listener on port 1022 after final reboots |
| Container configuration equivalence | All 15 match IDs, images, commands, environment, user, mounts, ports, security settings and network addresses |
| Application listeners | 11 published TCP bindings and 3 unpublished container listeners passed |
| Runtime versions | 13 × Node v22.23.5; 2 × Nginx 1.30.7 |
| Nginx configuration | Edge and backhaul `nginx -t` pass |
| Coding-lab sandbox through its Docker client | Passed; pinned Node image returns v22.23.5 |
| Wildcard certificate renewal | DNS-DigitalOcean Certbot dry run passed |

The sandbox smoke used the configured runner context/image and its normal restrictions: no network, read-only filesystem, UID/GID 65534, all capabilities dropped, no-new-privileges, 32 PIDs, 0.5 CPU and 128 MB memory/swap limit. Its temporary container was removed automatically.

The application host's 52 audited host-configuration files are byte-identical to the checkpoint, with none missing. The edge's 105 audited files have none missing; only sshd_config differs through upstream comments and AcceptEnv additions for COLORTERM/NO_COLOR. Its authentication policy is unchanged and syntax/access checks pass. Docker recreated the generated default-bridge network ID; that infrastructure identifier is excluded from address/configuration equivalence.

The MCP gateway retried twice with `Production dependencies not ready` while authentication started, then logged successful startup. Its restart count remained 2 at final health verification; the other 14 production containers have zero restarts. No configuration mismatch or unexpected running container was found.

The edge's Certbot timer and existing root cron renewal/restart commands remain in place. Existing certificates are valid through December 27–28; the wildcard staging renewal simulation succeeded without replacing the live certificate.

### Public HTTPS checks

All checks used normal TLS verification. All ten passed after both hosts were restored:

| Request | Expected / actual |
| --- | --- |
| GET beta.ngx-workshop.io/ | 200 |
| GET admin.ngx-workshop.io/ | 200 |
| GET auth.ngx-workshop.io/ | 200 |
| GET beta.ngx-workshop.io/api/documents/navigation/sections | 200 |
| GET mcp.ngx-workshop.io/.well-known/oauth-protected-resource/mcp | 200; correct MCP resource URL |
| GET auth.ngx-workshop.io/.well-known/oauth-authorization-server | 200 |
| GET auth.ngx-workshop.io/api/auth/validate-access-token | 200 |
| Unauthenticated POST mcp.ngx-workshop.io/mcp | 401 |
| Unauthenticated POST admin.ngx-workshop.io/api/publisher/tools with allowed Origin | 401 |
| Allowed-Origin publishing OPTIONS preflight | 204 |

These establish host/runtime recovery and the listed public behaviors. Signed-in Google/GitHub flows, authenticated authoring and full user journeys were not exercised. No paid generation, database migration, credential rotation or full application CI suite was run during the OS maintenance.

## Local Git synchronization

All 14 relevant main checkouts were synchronized to their published runtime security commits, with byte comparisons and working-file hashes confirming preservation. A final native Git fetch again found all 14 HEADs aligned with origin/main before this maintenance-record commit.

The Nginx documentation is updated by this completion commit. All other service checkouts remain at their published security commits. Service-auth retains exactly the user's pre-existing `authentication.controller.ts` edit and untracked `sign-out.spec.ts`; neither was included in the security deployment or synchronization commits. Documentation commits use `[skip ci]` to avoid another automatic production deployment.

## References

- https://documentation.ubuntu.com/release-notes/26.04/
- https://ubuntu.com/server/docs/how-to/software/upgrade-your-release/
- https://docs.docker.com/engine/install/ubuntu/
- https://docs.docker.com/engine/release-notes/29/
- https://docs.docker.com/engine/storage/containerd/
- https://docs.digitalocean.com/products/snapshots/how-to/snapshot-droplets/
- https://docs.digitalocean.com/products/snapshots/details/pricing/
