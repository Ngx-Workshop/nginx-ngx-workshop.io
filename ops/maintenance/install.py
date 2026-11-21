#!/usr/bin/env python3
"""Install bounded host logging/cache retention and remove obsolete journals."""
import os
from pathlib import Path
import re
import shutil
import socket
import subprocess


def run(*args):
    subprocess.run(args, check=True)


def main():
    if os.geteuid() != 0 or not socket.gethostname().startswith(('nodejs-', 'nginx-')):
        raise SystemExit('Run as root on an NGX Workshop NodeJS or Nginx host.')
    print('HOST', socket.gethostname(), flush=True)
    run('df', '-B1', '/')
    current = Path('/etc/machine-id').read_text().strip()
    if not re.fullmatch(r'[0-9a-f]{32}', current):
        raise SystemExit('Invalid current machine identity')
    pid = subprocess.check_output(
        ['systemctl', 'show', '--property=MainPID', '--value', 'systemd-journald'],
        text=True).strip()
    opened = []
    for fd in Path('/proc', pid, 'fd').iterdir():
        try:
            opened.append(os.readlink(fd))
        except OSError:
            pass
    journal_root = Path('/var/log/journal')
    removed = 0
    for directory in journal_root.iterdir():
        if (directory.is_symlink() or not directory.is_dir()
                or not re.fullmatch(r'[0-9a-f]{32}', directory.name)
                or directory.name == current):
            continue
        if any(p.startswith(str(directory) + '/') for p in opened):
            raise SystemExit('Historical journal is open; refusing removal')
        size = int(subprocess.check_output(['du', '-s', '-B1', str(directory)]).split()[0])
        shutil.rmtree(directory)
        removed += size
    print('HISTORICAL_JOURNAL_BYTES_REMOVED', removed, flush=True)
    config = Path('/etc/systemd/journald.conf.d/90-ngx-retention.conf')
    config.parent.mkdir(parents=True, exist_ok=True)
    config.write_text('[Journal]\nSystemMaxUse=128M\nRuntimeMaxUse=32M\n'
                      'SystemMaxFileSize=16M\nMaxRetentionSec=7day\nMaxFileSec=1day\n')
    service = Path('/etc/systemd/system/ngx-docker-cache-prune.service')
    service.write_text('[Unit]\nDescription=Bound unused Docker build cache\n'
                       'After=docker.service\nConditionPathExists=/var/run/docker.sock\n\n'
                       '[Service]\nType=oneshot\nNice=19\nIOSchedulingClass=idle\n'
                       'ExecStart=/usr/bin/flock -n /run/lock/ngx-docker-cache-prune.lock '
                       '/usr/bin/docker builder prune --force --all --keep-storage 512MB\n')
    Path('/etc/systemd/system/ngx-docker-cache-prune.timer').write_text(
        '[Unit]\nDescription=Hourly unused Docker cache retention\n\n'
        '[Timer]\nOnBootSec=15min\nOnUnitActiveSec=1h\nRandomizedDelaySec=5min\n'
        'Persistent=true\n\n[Install]\nWantedBy=timers.target\n')
    run('systemctl', 'daemon-reload')
    run('systemctl', 'restart', 'systemd-journald')
    run('journalctl', '--rotate')
    run('journalctl', '--vacuum-size=128M', '--vacuum-time=7days')
    run('systemctl', 'enable', '--now', 'ngx-docker-cache-prune.timer')
    # One-time reclaim of all unused build cache; images/containers/volumes stay intact.
    result = subprocess.run(['docker', 'builder', 'prune', '--force', '--all'],
                            capture_output=True, text=True, check=True)
    print('\n'.join(result.stdout.splitlines()[-2:]), flush=True)
    run('journalctl', '--disk-usage')
    run('docker', 'system', 'df')
    run('df', '-B1', '/')


if __name__ == '__main__':
    main()
