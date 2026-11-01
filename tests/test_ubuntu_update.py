import contextlib
import io
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

from test_xget import xget, MODULE_PATH


class UbuntuUpdateTests(unittest.TestCase):
    def test_version_matches_document_and_cli(self):
        output = subprocess.check_output([xget.sys.executable, str(MODULE_PATH), '--version'], text=True)
        self.assertEqual(output.strip(), 'xget.py ' + xget.VERSION)
        self.assertIn('# xGet ' + xget.VERSION, (MODULE_PATH.parent / 'README.md').read_text(encoding='utf-8'))

    def test_installer_source_launcher_and_preservation(self):
        script = (MODULE_PATH.parent / 'install_ubuntu.sh').read_text()
        self.assertIn('"$source_dir/xget.py" "$install_dir/xget.py"', script)
        self.assertIn('exec "$HOME/.local/share/xget/venv/bin/python" "$HOME/.local/share/xget/xget.py" "$@"', script)
        self.assertIn('[ ! -e "$install_dir/cookies.txt" ]', script)
        self.assertIn('"yt-dlp[default]"', script)
        self.assertIn('"$launcher" --version', script)
        self.assertIn('app.youtube_preflight()', script)
        self.assertNotIn('rm ', script)

    def test_uninstaller_keeps_user_data(self):
        script = (MODULE_PATH.parent / 'uninstall_ubuntu.sh').read_text()
        self.assertNotIn('find ', script)
        self.assertNotIn('-r', script)
        self.assertNotIn('cookies.txt', script)

    def test_deno_home_path_without_path(self):
        # Patch platform after creating concrete paths so this runs on Windows too.
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            deno = home / '.deno/bin/deno'
            deno.parent.mkdir(parents=True)
            deno.write_bytes(b'fake')
            with patch.object(xget.shutil, 'which', return_value=None), patch.object(xget.Path, 'home', return_value=home), patch.object(xget.os, 'access', return_value=True), patch.object(xget.os, 'name', 'posix'):
                # pathlib chooses its concrete class based on os.name; use host class.
                with patch.object(xget, 'Path', type(home)):
                    with patch.object(type(home), 'home', return_value=home):
                        self.assertEqual(xget.tool_path('deno'), str(deno))

    def test_missing_deno_version(self):
        with patch.object(xget, 'tool_path', return_value=None):
            self.assertIsNone(xget.deno_version())

    def test_deno_version_parsing(self):
        result = subprocess.CompletedProcess([], 0, 'deno 2.8.1 (stable)\nv8 test', '')
        with patch.object(xget.subprocess, 'run', return_value=result):
            self.assertEqual(xget.deno_version('/custom path/deno'), '2.8.1')

    def test_preflight_missing_and_outdated_components(self):
        ready = {'Deno': '2.8.1', 'FFmpeg': '/usr/bin/ffmpeg', 'yt-dlp': '2026.06.09', 'EJS': '1.0'}
        for field in ready:
            status = dict(ready, **{field: None})
            with self.subTest(field=field), patch.object(xget, 'youtube_environment', return_value=status), patch.object(xget, 'get_youtube_dl', return_value=object), contextlib.redirect_stdout(io.StringIO()) as out:
                self.assertFalse(xget.youtube_preflight())
                self.assertIn('Run menu 9', out.getvalue())
        with patch.object(xget, 'youtube_environment', return_value=dict(ready, Deno='2.2.0')):
            self.assertFalse(xget.youtube_preflight())

    def test_preflight_ready(self):
        with patch.object(xget, 'youtube_environment', return_value={'Deno': '2.3.0', 'FFmpeg': 'ffmpeg', 'yt-dlp': '2026.06.09', 'EJS': '1'}), patch.object(xget, 'get_youtube_dl', return_value=object):
            self.assertTrue(xget.youtube_preflight())

    def test_preflight_blocks_download_before_input(self):
        with patch.object(xget, 'youtube_preflight', return_value=False), patch.object(xget, 'read_youtube_urls') as read:
            xget.youtube_download()
            read.assert_not_called()

    def test_explicit_runtime_path_and_no_delays(self):
        with patch.object(xget, 'tool_path', side_effect=lambda name: '/home/a path/.deno/bin/deno' if name == 'deno' else 'ffmpeg'):
            options = xget.youtube_options(Path('output'), None, None)
        self.assertEqual(options['js_runtimes']['deno']['path'], '/home/a path/.deno/bin/deno')
        for key in ('sleep_interval', 'max_sleep_interval', 'sleep_interval_requests'):
            self.assertNotIn(key, options)
        self.assertEqual(options['concurrent_fragment_downloads'], 4)
        self.assertNotIn('10-15', MODULE_PATH.read_text(encoding='utf-8'))

    def test_403_guidance_never_refreshes(self):
        with patch.object(xget, 'youtube_environment', return_value={'Deno': None}), patch.object(xget, 'refresh_youtube_components') as refresh, contextlib.redirect_stdout(io.StringIO()) as out:
            xget.youtube_403_guidance('HTTP Error 403: Forbidden')
            self.assertIn('cookies/session', out.getvalue())
            self.assertIn('Run menu 9', out.getvalue())
            refresh.assert_not_called()

    def test_refresh_preserves_all_user_files(self):
        with tempfile.TemporaryDirectory() as directory:
            app = Path(directory)
            names = ('cookies.txt', '.xget-youtube-archive.txt', 'xget.session', 'xget-settings.json', 'downloads/movie.mp4')
            for name in names:
                file = app / name
                file.parent.mkdir(exist_ok=True)
                file.write_bytes(name.encode())
            with patch.object(xget, 'APP_DIR', app), patch.object(xget, 'ask', return_value='y'), patch.object(xget, 'refresh_deno', return_value=True), patch.object(xget, 'run', return_value=True), patch.object(xget, 'youtube_preflight', return_value=True):
                xget.refresh_youtube_components()
            for name in names:
                self.assertEqual((app / name).read_bytes(), name.encode())

    def test_storage_spaces_persist(self):
        with tempfile.TemporaryDirectory() as directory:
            app = Path(directory)
            destination = app / 'folder with spaces'
            with patch.object(xget, 'SETTINGS_FILE', app / 'xget-settings.json'):
                self.assertTrue(xget.save_settings({'download_dir': str(destination), 'mirror_dir': str(destination / 'web')}))
                self.assertEqual(xget.downloads_dir(False), destination)
                self.assertEqual(xget.home_dir(False), destination / 'web')
                self.assertEqual(xget.load_settings()['download_dir'], str(destination))

    def test_missing_mount_does_not_create_directory(self):
        # POSIX-style path traversal is tested independently of the host platform.
        path = MagicMock()
        path.absolute.return_value.parts = ('/', 'mnt', 'unmounted', 'xGet')
        with patch.object(xget.os, 'name', 'posix'), patch.object(xget, 'Path', return_value=path), patch.object(xget.os.path, 'ismount', return_value=False):
            with self.assertRaisesRegex(OSError, 'unavailable'):
                xget.ensure_output_dir(path)
            path.mkdir.assert_not_called()

    def test_fallback_requires_consent_and_keeps_setting(self):
        with patch.object(xget, 'configured_path', return_value=Path('missing')), patch.object(xget, 'ensure_output_dir', side_effect=[OSError('unavailable'), Path('default')]), patch.object(xget, 'ask', return_value='y'):
            self.assertEqual(xget.storage_dir('download_dir', Path('default')), Path('default'))
        with patch.object(xget, 'configured_path', return_value=Path('missing')), patch.object(xget, 'ensure_output_dir', side_effect=OSError('unavailable')), patch.object(xget, 'ask', return_value='n'):
            with self.assertRaises(OSError):
                xget.storage_dir('download_dir', Path('default'))