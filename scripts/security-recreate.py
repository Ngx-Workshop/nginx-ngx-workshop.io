#!/usr/bin/env python3
"""Replace one container with a reviewed local image, retaining rollback state.

Run on the Docker host as root. Inspection snapshots contain credentials and
remain private on that host. No images, volumes, or previous containers are pruned.
"""
import argparse
import copy
import http.client
import json
import os
from pathlib import Path
import socket
import subprocess
import time
from urllib.parse import quote


class DockerHTTP(http.client.HTTPConnection):
    def connect(self):
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.settimeout(90)
        self.sock.connect('/var/run/docker.sock')


def api(method, path, body=None):
    conn = DockerHTTP('localhost', timeout=90)
    conn.request(method, path, json.dumps(body) if body is not None else None,
                 {'Content-Type': 'application/json'})
    response = conn.getresponse()
    raw = response.read()
    conn.close()
    if response.status >= 400:
        raise RuntimeError(f'Docker {method} {path.split("?")[0]} returned {response.status}')
    return json.loads(raw) if raw else None


def docker(*args):
    return subprocess.check_output(['docker', *args], text=True,
                                   stderr=subprocess.PIPE).strip()


def endpoints(old):
    result = {}
    for network, value in old['NetworkSettings']['Networks'].items():
        item = {key: value[key] for key in ('IPAMConfig', 'Links', 'DriverOpts')
                if value.get(key)}
        # Preserve addresses: legacy Nginx upstreams can cache Docker DNS.
        if network != 'bridge':
            item.setdefault('IPAMConfig', {})
            if value.get('IPAddress'):
                item['IPAMConfig']['IPv4Address'] = value['IPAddress']
            if value.get('GlobalIPv6Address'):
                item['IPAMConfig']['IPv6Address'] = value['GlobalIPv6Address']
            item['Aliases'] = [alias for alias in value.get('Aliases') or []
                               if alias not in (old['Id'], old['Id'][:12])]
        result[network] = item
    return result


def payload(old, image, image_config, runner_image):
    config = copy.deepcopy(old['Config'])
    config['Image'] = image
    config.pop('MacAddress', None)
    config.pop('OnBuild', None)
    updated = dict(entry.split('=', 1) for entry in config.get('Env') or [])
    base_env = dict(entry.split('=', 1) for entry in image_config.get('Env') or [])
    for key in ('NODE_VERSION', 'YARN_VERSION', 'NGINX_VERSION', 'NJS_VERSION', 'PKG_RELEASE'):
        if key in base_env:
            updated[key] = base_env[key]
    if runner_image:
        updated['RUNNER_IMAGE'] = runner_image
    config['Env'] = [f'{key}={value}' for key, value in updated.items()]
    config.setdefault('Labels', {})
    config['Labels'] = config['Labels'] or {}
    config['Labels']['io.ngx-workshop.runtime-patch'] = '2026-11-21'
    host = copy.deepcopy(old['HostConfig'])
    if host.get('AutoRemove') or host.get('VolumesFrom'):
        raise RuntimeError('Unsupported auto-remove or volumes-from container')
    existing = {m['Target'] for m in host.get('Mounts') or []}
    existing.update(b.split(':')[1] for b in host.get('Binds') or [])
    for mount in old['Mounts']:
        if mount['Destination'] in existing or mount['Type'] not in ('bind', 'volume'):
            continue
        source = mount.get('Name') if mount['Type'] == 'volume' else mount['Source']
        host.setdefault('Binds', [])
        host['Binds'] = host['Binds'] or []
        host['Binds'].append(f'{source}:{mount["Destination"]}:{"rw" if mount["RW"] else "ro"}')
    config['HostConfig'] = host
    config['NetworkingConfig'] = {'EndpointsConfig': endpoints(old)}
    return config


def check(name, kind, version, port):
    info = json.loads(docker('inspect', name))[0]
    if not info['State']['Running'] or info['State']['Restarting']:
        return False
    if info['State'].get('Health', {}).get('Status') == 'unhealthy':
        return False
    if kind == 'nginx':
        docker('exec', name, 'nginx', '-t')
        output = subprocess.run(['docker', 'exec', name, 'nginx', '-v'],
                                capture_output=True, text=True, check=True)
        return f'nginx/{version}' in output.stderr + output.stdout
    if docker('exec', name, 'node', '--version') != 'v' + version:
        return False
    if port:
        expression = ("const n=require('net');const s=n.connect(" + str(port)
                      + ",'127.0.0.1',()=>{s.end();process.exit(0)});"
                      "s.on('error',()=>process.exit(1));setTimeout(()=>process.exit(1),1500)")
        docker('exec', name, 'node', '-e', expression)
    return True


def deploy(args):
    os.umask(0o077)
    directory = Path(args.directory)
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    old = json.loads(docker('inspect', args.name))[0]
    image = json.loads(docker('image', 'inspect', args.image))[0]
    previous = args.name + '.before-security-20261121'
    snapshot = directory / (args.name + '.before.json')
    if snapshot.exists():
        raise RuntimeError('Snapshot already exists; inspect before retrying')
    snapshot.write_text(json.dumps(old, indent=2))
    snapshot.chmod(0o600)
    body = payload(old, image['Id'], image['Config'], args.runner_image)
    (directory / (args.name + '.replacement.json')).write_text(json.dumps(body, indent=2))
    if not args.apply:
        print(f'{args.name}: prepared private snapshot; no replacement performed')
        return
    # Keep the previous writable layer and image for explicit rollback.
    old_id = old['Id']
    docker('stop', '--time', '30', old_id)
    renamed = False
    candidate = None
    disconnected = []
    try:
        docker('rename', old_id, previous)
        renamed = True
        api('POST', f'/containers/{old_id}/update', {'RestartPolicy': {'Name': 'no'}})
        for network in old['NetworkSettings']['Networks']:
            api('POST', f'/networks/{quote(network, safe="")}/disconnect', {'Container': old_id})
            disconnected.append(network)
        result = api('POST', '/containers/create?name=' + quote(args.name), body)
        candidate = result['Id']
        api('POST', f'/containers/{candidate}/start')
        deadline = time.monotonic() + 60
        while time.monotonic() < deadline:
            try:
                if check(args.name, args.kind, args.version, args.port):
                    restarts = json.loads(docker('inspect', args.name))[0]['RestartCount']
                    time.sleep(5)
                    stable = json.loads(docker('inspect', args.name))[0]['RestartCount'] == restarts
                    if stable and check(args.name, args.kind, args.version, args.port):
                        (directory / (args.name + '.success')).write_text(image['Id'] + '\n')
                        print(f'{args.name}: verified {args.version}; rollback={previous}', flush=True)
                        return
            except subprocess.CalledProcessError:
                pass
            time.sleep(2)
        raise RuntimeError('Replacement failed readiness checks')
    except Exception as failure:
        (directory / (args.name + '.failure')).write_text(repr(failure))
        if candidate:
            # This removes only the failed replacement; volumes are retained.
            docker('rm', '-f', candidate)
        if renamed:
            docker('rename', old_id, args.name)
        for network in disconnected:
            api('POST', f'/networks/{quote(network, safe="")}/connect',
                {'Container': old_id, 'EndpointConfig': endpoints(old)[network]})
        api('POST', f'/containers/{old_id}/update', {'RestartPolicy': old['HostConfig']['RestartPolicy']})
        docker('start', old_id)
        raise RuntimeError('Replacement failed; previous container restored') from None


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('name')
    parser.add_argument('image')
    parser.add_argument('--kind', choices=['node', 'nginx'], required=True)
    parser.add_argument('--version', required=True)
    parser.add_argument('--port', type=int)
    parser.add_argument('--runner-image')
    parser.add_argument('--directory', required=True)
    parser.add_argument('--apply', action='store_true')
    try:
        deploy(parser.parse_args())
    except Exception as error:
        # Never echo docker inspect/configuration or subprocess output here.
        print(str(error) if isinstance(error, RuntimeError) else
              'Deployment error; inspect private host logs.', flush=True)
        raise SystemExit(1)
