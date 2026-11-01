"""Regression tests for the xGet 2.15 Torrent and YouTube multi-job update."""
import contextlib
import importlib.util
import io
import json
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch

MODULE = Path(__file__).resolve().parents[1] / "xget.py"
spec = importlib.util.spec_from_file_location("xget_torrent_test", MODULE)
xget = importlib.util.module_from_spec(spec)
spec.loader.exec_module(xget)


class TorrentUpgradeTests(unittest.TestCase):
    def test_magnet_parameter_order_and_v2(self):
        self.assertTrue(xget.valid_magnet_uri("magnet:?dn=Example&xt=urn:btih:ABCD1234"))
        self.assertTrue(xget.valid_magnet_uri("magnet:?xt=urn:btmh:1220ABCD&dn=Example"))
        self.assertFalse(xget.valid_magnet_uri("magnet:?dn=Example"))
        self.assertFalse(xget.valid_magnet_uri("https://example.org/torrent"))

    def test_torrent_runtime_flags_are_verified(self):
        prefs = dict(xget.TORRENT_DEFAULTS, torrent_concurrent=2,
                     torrent_download_limit="2M", torrent_upload_limit="400K",
                     torrent_seed_time=60, torrent_seed_ratio="1.5", torrent_max_peers=100)
        args = xget.add_torrent_options(["aria2c"], ["magnet:?xt=urn:btih:ABCDEF"], 2, Path("files"), prefs)
        for flag in ("--max-concurrent-downloads=2", "--max-overall-download-limit=2M",
                     "--max-overall-upload-limit=400K", "--seed-time=60", "--seed-ratio=1.5",
                     "--bt-max-peers=100", "--bt-save-metadata=true", "--check-integrity=true",
                     "--bt-remove-unselected-file=false"):
            self.assertIn(flag, args)
        self.assertEqual(args[-1], "magnet:?xt=urn:btih:ABCDEF")

    def test_single_torrent_file_selection(self):
        args = xget.add_torrent_options(["aria2c"], ["test.torrent"], 1,
                                        preferences=xget.TORRENT_DEFAULTS, selected_files="1,3-5")
        self.assertIn("--select-file=1,3-5", args)
        with self.assertRaises(ValueError):
            xget.add_torrent_options(["aria2c"], ["one.torrent", "two.torrent"], 2,
                                     preferences=xget.TORRENT_DEFAULTS, selected_files="1")
        with self.assertRaises(ValueError):
            xget.add_torrent_options(["aria2c"], ["magnet:?xt=urn:btih:123"], 1,
                                     preferences=xget.TORRENT_DEFAULTS, selected_files="1")

    def test_select_files_validation(self):
        self.assertIsNone(xget.parse_torrent_file_selection("  "))
        self.assertEqual(xget.parse_torrent_file_selection(" 1, 3 - 5"), "1,3-5")
        for raw in ("0", "1-0", "1,,2", "../test", "1;--dir=/tmp", "1-a", "2-1"):
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                xget.parse_torrent_file_selection(raw)

    def test_bad_torrent_settings_and_valid_caps(self):
        for key, value in (("torrent_download_limit", "-1"), ("torrent_upload_limit", "1M --foo"),
                           ("torrent_seed_ratio", "NaN"), ("torrent_seed_time", "-1"),
                           ("torrent_max_peers", "0"), ("torrent_concurrent", "20")):
            with self.subTest(key=key), self.assertRaises(ValueError):
                xget.validate_torrent_setting(key, value)
        self.assertEqual(xget.validate_torrent_setting("torrent_download_limit", "200k"), "200K")
        self.assertEqual(xget.validate_torrent_setting("torrent_seed_time", "60"), 60)

    def test_torrent_preferences_keep_other_settings(self):
        with tempfile.TemporaryDirectory() as tmp:
            location = Path(tmp) / "xget-settings.json"
            location.write_text(json.dumps({"download_dir": "keep-me", "torrent_max_peers": "broken"}))
            with patch.object(xget, "SETTINGS_FILE", location):
                with contextlib.redirect_stdout(io.StringIO()):
                    self.assertEqual(xget.torrent_preferences()["torrent_max_peers"], 55)
                self.assertEqual(xget.load_settings()["download_dir"], "keep-me")
                labels = iter(["2", "500K", "100K", "30", "1.0", "80", "y"])
                with patch.object(xget, "ask", side_effect=lambda *args: next(labels)):
                    xget.configure_torrent_preferences()
                stored = json.loads(location.read_text())
                self.assertEqual(stored["download_dir"], "keep-me")
                self.assertEqual(stored["torrent_max_peers"], 80)
                self.assertEqual(stored["torrent_download_limit"], "500K")

    def test_preview_does_not_download(self):
        import subprocess
        fake = subprocess.CompletedProcess([], 0, "[1] file-a.bin (10MiB)\\n[2] file-b.bin (20MiB)", "")
        with patch.object(xget.subprocess, "run", return_value=fake) as mock_run:
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertTrue(xget.torrent_file_preview("aria2c", "/path/test.torrent"))
        self.assertEqual(mock_run.call_args.args[0], ["aria2c", "--show-files=true", "/path/test.torrent"])

    def test_youtube_large_list_from_txt_and_host_validation(self):
        with tempfile.TemporaryDirectory() as tmp:
            file = Path(tmp) / "large youtube list.txt"
            file.write_text("https://www.youtube.com/watch?v=abc12345678\nhttps://youtu.be/def12345678\nhttps://youtube.com.evil.org/x\n", encoding="utf-8")
            with patch.object(xget, "ask", return_value="@"+str(file)):
                urls = xget.read_youtube_urls()
            self.assertEqual(len(urls), 2)

    def test_youtube_scheduler_stops_admitting_after_five_errors(self):
        submitted = []
        def fail_job(url, output, mode, cookie, index, monitor):
            submitted.append(index)
            with contextlib.suppress(xget.YoutubeRunStopped):
                monitor.record_error("test failure")
                if index == 1:
                    for _ in range(4):
                        monitor.record_error("test failure")
            return (url, False, "failed")
        urls = [f"https://youtu.be/{n:011d}" for n in range(20)]
        with patch.object(xget, "youtube_preflight", return_value=True), \
             patch.object(xget, "read_youtube_urls", return_value=urls), \
             patch.object(xget, "downloads_dir", return_value=Path("downloads")), \
             patch.object(xget, "sync_youtube_archive", return_value=(0, Path("downloads/archive"))), \
             patch.object(xget, "ask", side_effect=["2", "2"]), \
             patch.object(xget, "download_one_youtube", side_effect=fail_job), \
             contextlib.redirect_stdout(io.StringIO()):
            xget.youtube_download()
        self.assertTrue(submitted)
        self.assertLess(len(submitted), len(urls))
        self.assertLessEqual(len(submitted), 3)  # two active plus a possible race before stop

    def test_cleanup_preserves_aria2_resume_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            (folder / "torrent.data.aria2").write_bytes(b"resume")
            (folder / "random.part").write_bytes(b"partial")
            with patch.object(xget, "downloads_dir", return_value=folder), \
                 patch.object(xget, "ask", return_value="y"), \
                 contextlib.redirect_stdout(io.StringIO()):
                xget.cleanup_incomplete()
            self.assertTrue((folder / "torrent.data.aria2").exists())
            self.assertFalse((folder / "random.part").exists())


if __name__ == "__main__":
    unittest.main()

class InstallerParityTests(unittest.TestCase):
    def test_windows_install_verifies_same_version(self):
        installer = MODULE.parent / "install_windows.ps1"
        script = installer.read_text(encoding="utf-8")
        self.assertIn('sourceVersion', script)
        self.assertIn('installedVersion', script)
        self.assertIn('version mismatch after installation', script)

    def test_pause_does_not_traceback_on_interrupt(self):
        with patch('builtins.input', side_effect=KeyboardInterrupt), contextlib.redirect_stdout(io.StringIO()):
            xget.pause()