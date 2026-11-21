"""Real filesystem/rsync regression checks using disposable static sites."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

TEMPLATE_TEXT = globals().get('TEMPLATE_TEXT') or Path(__file__).with_name('deploy-static.sh.in').read_text()


@unittest.skipUnless(shutil.which('flock'), 'Requires Linux flock; executed on host and Ubuntu CI')
class StaticDeploymentTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='ngx-static-tests-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.destination = self.root / 'live'
        self.destination.mkdir()
        (self.destination / 'index.html').write_text('old index')
        (self.destination / 'obsolete-hash.js').write_text('old chunk')
        (self.destination / '.old-hidden').write_text('old hidden file')
        self.staging = self.root / 'staging/site/123-1'
        self.source = self.staging / 'site'
        self.source.mkdir(parents=True)
        (self.source / 'index.html').write_text('new index')
        (self.source / 'remoteEntry.js').write_text('new remote')
        (self.source / 'new-hash.js').write_text('new chunk')
        (self.root / 'locks').mkdir()
        tools = self.root / 'bin'
        tools.mkdir()
        docker = tools / 'docker'
        docker.write_text('#!/bin/sh\n[ "${FAIL_NGINX_CHECK:-0}" = 0 ]\n')
        docker.chmod(0o755)
        self.environment = dict(os.environ, PATH=str(tools) + ':' + os.environ['PATH'])
        self.script = self.root / 'deploy.sh'
        self.render()

    def render(self):
        self.script.write_text(TEMPLATE_TEXT.replace('@@PROJECT@@', 'site')
                              .replace('@@TARGET@@', str(self.destination))
                              .replace('@@ENTRIES@@', 'index.html remoteEntry.js')
                              .replace('/opt/ngx-frontend-staging/', str(self.root / 'staging') + '/')
                              .replace('/var/lock/', str(self.root / 'locks') + '/'))

    def deploy(self, release='123-1'):
        return subprocess.run(['sh', str(self.script), release], env=self.environment,
                              capture_output=True, text=True)

    def assert_old_site(self):
        self.assertEqual((self.destination / 'index.html').read_text(), 'old index')
        self.assertEqual({p.name for p in self.destination.iterdir()},
                         {'index.html', 'obsolete-hash.js', '.old-hidden'})

    def test_complete_release_deletes_stale_assets_and_preserves_mount_inode(self):
        inode = self.destination.stat().st_ino
        result = self.deploy()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.destination.stat().st_ino, inode)
        self.assertEqual({p.name for p in self.destination.iterdir()},
                         {'index.html', 'remoteEntry.js', 'new-hash.js'})
        self.assertFalse(self.staging.exists())

    def test_missing_remote_entry_keeps_previous_release(self):
        (self.source / 'remoteEntry.js').unlink()
        self.assertNotEqual(self.deploy().returncode, 0)
        self.assert_old_site()

    def test_missing_index_keeps_previous_release(self):
        (self.source / 'index.html').unlink()
        self.assertNotEqual(self.deploy().returncode, 0)
        self.assert_old_site()

    def test_build_symlink_is_rejected_before_promotion(self):
        (self.source / 'outside').symlink_to('/etc')
        self.assertNotEqual(self.deploy().returncode, 0)
        self.assert_old_site()

    def test_invalid_release_cannot_escape_staging(self):
        self.assertEqual(self.deploy('../../live').returncode, 2)
        self.assert_old_site()

    def test_nginx_visibility_failure_restores_previous_contents(self):
        self.environment['FAIL_NGINX_CHECK'] = '1'
        self.assertNotEqual(self.deploy().returncode, 0)
        self.assert_old_site()
        self.assertFalse(self.staging.exists())

    def test_destination_symlink_is_rejected(self):
        original = self.destination
        self.destination = self.root / 'linked-live'
        self.destination.symlink_to(original, target_is_directory=True)
        self.render()
        self.assertNotEqual(self.deploy().returncode, 0)
        self.assertEqual((original / 'index.html').read_text(), 'old index')


if __name__ == '__main__':
    unittest.main()
