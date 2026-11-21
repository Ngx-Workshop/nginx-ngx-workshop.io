#!/usr/bin/env python3
"""Build runtime-only patch images from the exact deployed application artifacts.

No production container is stopped. Private build logs and rollback inputs stay on
the Docker host. Run security-recreate.py separately to promote each image.
"""
import hashlib
import json
import os
from pathlib import Path
import subprocess

BASE = 'node:22.23.5-alpine@sha256:1314fb30ec37592d5845e5a160d522c0e680972aa534549940b8d73bde88481a'
SERVICES = {
    'ngx-auth-service': 3000, 'service-mcp-gateway': 3011,
    'service-ai-publisher': 3014, 'coding-labs': 3009,
    'service-user-metadata': 3004, 'ngx-mfe-orchestrator': 3001,
    'service-nestjs-assessment-test': 3005, 'document': 3007,
    'service-uploader': 3010, 'seed-service-nestjs': 3003,
    'ngx-workshop-bff': 3002, 'backstage': 3008,
    'service-navigational-list': 3006,
}


def docker(*args):
    return subprocess.check_output(['docker', *args], text=True,
                                   stderr=subprocess.PIPE).strip()


def main():
    os.umask(0o077)
    root = Path('/opt/ngx-releases/security-20261121')
    root.mkdir(mode=0o700, parents=True, exist_ok=True)
    docker('pull', BASE)
    assert docker('run', '--rm', BASE, 'node', '--version') == 'v22.23.5'
    results = []
    for name, port in SERVICES.items():
        print('Building ' + name, flush=True)
        old = json.loads(docker('inspect', name))[0]
        assert old['Config']['WorkingDir'] == '/usr/src/app'
        directory = root / 'build' / name
        directory.mkdir(parents=True, exist_ok=True)
        source = name + ':before-security-20261121'
        docker('tag', old['Image'], source)
        tag = name + ':security-20261121'
        lines = [f'FROM {source} AS deployed', f'FROM {BASE}', 'WORKDIR /usr/src/app']
        if name == 'coding-labs':
            lines.append('RUN apk add --no-cache docker-cli')
        lines += ['COPY --from=deployed /usr/src/app/ /usr/src/app/']
        if name == 'service-ai-publisher':
            lines.append('RUN mkdir -p /var/lib/ngx-publishing && chown node:node /var/lib/ngx-publishing')
        if old['Config'].get('User'):
            lines.append('USER ' + old['Config']['User'])
        lines += ['ENTRYPOINT ' + json.dumps(old['Config'].get('Entrypoint') or []),
                  'CMD ' + json.dumps(old['Config'].get('Cmd') or [])]
        (directory / 'Dockerfile').write_text('\n'.join(lines) + '\n')
        with (directory / 'build.log').open('w') as log:
            subprocess.run(['docker', 'build', '-t', tag, str(directory)],
                           stdout=log, stderr=subprocess.STDOUT, check=True)
        assert docker('run', '--rm', '--entrypoint', 'node', tag, '--version') == 'v22.23.5'
        # The dist tree is byte-for-byte the deployed application, not stale source.
        script = 'cd /usr/src/app && find dist -type f -exec sha256sum {} \\; | sort'
        before = docker('exec', name, 'sh', '-c', script)
        after = docker('run', '--rm', '--entrypoint', 'sh', tag, '-c', script)
        assert before == after, name + ': deployed application bytes differ'
        if name == 'ngx-auth-service':
            docker('run', '--rm', '--entrypoint', 'node', tag, '-e',
                   'require("bcrypt").hashSync("runtime-patch-test",4)')
        results.append({'name': name, 'port': port, 'previous_image': old['Image'],
                        'candidate': tag, 'candidate_image': docker('image', 'inspect', tag, '--format', '{{.Id}}'),
                        'dist_manifest_sha256': hashlib.sha256(before.encode()).hexdigest()})
        (root / 'candidates.json').write_text(json.dumps(results, indent=2))
        print(name + ': built; Node version and identical application verified', flush=True)
    (root / 'build.success').write_text('13 candidates verified\n')


if __name__ == '__main__':
    try:
        main()
    except Exception:
        print('Build failed; see private per-service build log. Production containers unchanged.', flush=True)
        raise SystemExit(1)
