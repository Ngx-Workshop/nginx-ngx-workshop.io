# Host disk retention

Run `python3 install.py` as root on the existing NodeJS/Nginx host to install:

- Persistent system journals bounded to 128 MiB and seven days, with 16 MiB files;
  volatile journals bounded to 32 MiB. The current machine journal remains active.
- An hourly `ngx-docker-cache-prune.timer` that prunes unused Docker builder cache
  toward 512 MB without an age filter. Docker protects cache still in use and
  image-referenced data; this is not a hard cap on running image storage.
- A one-time removal of journal directories belonging to other machine identities
  and all unused builder cache. Journal symlinks/current identity/open journal
  directories are protected. Running containers, images and volumes are untouched.

The installer prints before/after filesystem usage. It does not print credentials.
No Docker daemon restart or application restart is required. Existing per-service
post-deployment cleanup still runs; the timer prevents recent cache from growing
without cleanup merely because it is younger than 24 hours.

## Applied 2026-11-21

| Host | Before (decimal GB) | After journal/cache cleanup (decimal GB) |
| --- | ---: | ---: |
| NodeJS | 21.2985 | 11.5385 |
| Nginx | 8.4568 | 5.9796 |

Approximately 12.24 GB of allocated disk space was recovered. The historical journal
directories accounted for 3,991,605,248 bytes on NodeJS and 2,477,907,968 on Nginx.
Docker reported zero remaining build cache on both hosts immediately afterward.
These figures are live filesystem usage, not newly created snapshot measurements.

## Frontend accumulation

Static sites used overwrite-only SCP into the served directory. This left old
hashed JavaScript, source maps and development/production build variants together.
The repaired workflows stage the full existing build, then run their local
`scripts/deploy-static.sh`, rendered from `../frontend/deploy-static.sh.in`.
The helper uses delayed rsync updates/deletion, preserves the Nginx bind-mount
directory inode, verifies expected entrypoints through the container and restores
prior content on promotion failure. Temporary staging/backup is removed on success;
failed rollback retains recovery files. Each project's workflow cleans failed
upload staging when it can reconnect to the host.

Existing build configurations and package publishing are preserved. No runtime
dependencies, federation interfaces or application code were changed. The seed's
helper is customized by the CLI's existing whole-tree project-name replacement.
Seven real-filesystem/rsync regression cases passed on Linux using disposable
directories and a test double only for the final Nginx visibility command.

## Completed frontend rollout

All 27 site deployment workflows succeeded. Shared maintenance/helper CI passed:
https://github.com/Ngx-Workshop/nginx-ngx-workshop.io/actions/runs/44938704104

Live Nginx entrypoint checks passed for all 27 sites; public admin, workshop, auth
and design-system roots returned HTTPS 200. All 13 backend heartbeats passed.
Both journal daemons and cache timers are active; manually running each cache
service returned Result=success.

Final Nginx filesystem usage after all static redeployments: 5,402,210,304 bytes
(5.40 decimal GB). Admin shell fell from 637 files/16 main bundles to 298 files/one
main bundle; workshop fell from 358 files/seven main bundles to 282 files/one main
bundle. The staging tree contains only the per-project parent directories.

NodeJS remains approximately 11.54 GB; total recovered space across both hosts is
approximately 12.82 GB versus the investigation baseline. Fresh snapshots are
needed to capture this reduction; existing snapshot objects were not modified.

| Repository | Successful deployment |
| --- | --- |
| app-authentication | [Run 44938352953](https://github.com/Ngx-Workshop/app-authentication/actions/runs/44938352953) |
| mfe-shell-admin | [Run 44938363115](https://github.com/Ngx-Workshop/mfe-shell-admin/actions/runs/44938363115) |
| mfe-shell-workshop | [Run 44938368548](https://github.com/Ngx-Workshop/mfe-shell-workshop/actions/runs/44938368548) |
| mfe-structural-footer | [Run 44938374680](https://github.com/Ngx-Workshop/mfe-structural-footer/actions/runs/44938374680) |
| mfe-structural-header | [Run 44938385906](https://github.com/Ngx-Workshop/mfe-structural-header/actions/runs/44938385906) |
| mfe-structural-navigation | [Run 44938391886](https://github.com/Ngx-Workshop/mfe-structural-navigation/actions/runs/44938391886) |
| mfe-user-journey-admin-ai-publisher | [Run 44938401556](https://github.com/Ngx-Workshop/mfe-user-journey-admin-ai-publisher/actions/runs/44938401556) |
| mfe-user-journey-admin-assessment-test | [Run 44938409203](https://github.com/Ngx-Workshop/mfe-user-journey-admin-assessment-test/actions/runs/44938409203) |
| mfe-user-journey-admin-asset-manager | [Run 44938416029](https://github.com/Ngx-Workshop/mfe-user-journey-admin-asset-manager/actions/runs/44938416029) |
| mfe-user-journey-admin-backstage | [Run 44938422240](https://github.com/Ngx-Workshop/mfe-user-journey-admin-backstage/actions/runs/44938422240) |
| mfe-user-journey-admin-chat | [Run 44938923768](https://github.com/Ngx-Workshop/mfe-user-journey-admin-chat/actions/runs/44938923768) |
| mfe-user-journey-admin-coding-labs | [Run 44938436187](https://github.com/Ngx-Workshop/mfe-user-journey-admin-coding-labs/actions/runs/44938436187) |
| mfe-user-journey-admin-dashboard | [Run 44938639742](https://github.com/Ngx-Workshop/mfe-user-journey-admin-dashboard/actions/runs/44938639742) |
| mfe-user-journey-landing-page | [Run 44938653959](https://github.com/Ngx-Workshop/mfe-user-journey-landing-page/actions/runs/44938653959) |
| mfe-user-journey-admin-document-editor | [Run 44938663760](https://github.com/Ngx-Workshop/mfe-user-journey-admin-document-editor/actions/runs/44938663760) |
| mfe-user-journey-admin-mcp-gateway | [Run 44938679603](https://github.com/Ngx-Workshop/mfe-user-journey-admin-mcp-gateway/actions/runs/44938679603) |
| mfe-user-journey-admin-mfe-orchestrator | [Run 44938688519](https://github.com/Ngx-Workshop/mfe-user-journey-admin-mfe-orchestrator/actions/runs/44938688519) |
| mfe-user-journey-admin-navigational-list | [Run 44938696661](https://github.com/Ngx-Workshop/mfe-user-journey-admin-navigational-list/actions/runs/44938696661) |
| mfe-user-journey-admin-user-management | [Run 44938705070](https://github.com/Ngx-Workshop/mfe-user-journey-admin-user-management/actions/runs/44938705070) |
| mfe-user-journey-assessment-test | [Run 44938713640](https://github.com/Ngx-Workshop/mfe-user-journey-assessment-test/actions/runs/44938713640) |
| mfe-user-journey-coding-labs | [Run 44938720993](https://github.com/Ngx-Workshop/mfe-user-journey-coding-labs/actions/runs/44938720993) |
| mfe-user-journey-dashboard | [Run 44938731446](https://github.com/Ngx-Workshop/mfe-user-journey-dashboard/actions/runs/44938731446) |
| mfe-user-journey-settings | [Run 44938739038](https://github.com/Ngx-Workshop/mfe-user-journey-settings/actions/runs/44938739038) |
| mfe-user-journey-workshops | [Run 44938746898](https://github.com/Ngx-Workshop/mfe-user-journey-workshops/actions/runs/44938746898) |
| ngx-local-storage-broker | [Run 44938754913](https://github.com/Ngx-Workshop/ngx-local-storage-broker/actions/runs/44938754913) |
| ngx-workshop-design-system | [Run 44938763009](https://github.com/Ngx-Workshop/ngx-workshop-design-system/actions/runs/44938763009) |
| seed-mfe-remote | [Run 44938770948](https://github.com/Ngx-Workshop/seed-mfe-remote/actions/runs/44938770948) |
