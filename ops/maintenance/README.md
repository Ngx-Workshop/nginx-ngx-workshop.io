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
