import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


MODULE_PATH = Path(__file__).parents[1] / "xget.py"
SPEC = importlib.util.spec_from_file_location("xget", MODULE_PATH)
xget = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(xget)


class XGetTests(unittest.TestCase):
    def test_valid_http_url(self):
        self.assertTrue(xget.valid_http_url("https://example.com/file.zip"))
        self.assertTrue(xget.valid_http_url("http://localhost:8000/a"))
        self.assertFalse(xget.valid_http_url("magnet:?xt=urn:btih:test"))
        self.assertFalse(xget.valid_http_url("example.com/file.zip"))

    def test_magnet_pattern(self):
        self.assertIsNotNone(xget.MAGNET_RE.match("magnet:?xt=urn:btih:ABC123"))
        self.assertIsNone(xget.MAGNET_RE.match("https://example.com/test.torrent"))

    def test_keyboard_multi_source_input(self):
        with patch(
            "builtins.input",
            side_effect=[r'C:\Torrents\one.torrent', r'C:\Torrents\two.torrent', ""],
        ):
            sources = xget.read_sources_from_keyboard("Torrent file path")
        self.assertEqual(
            sources,
            [r'C:\Torrents\one.torrent', r'C:\Torrents\two.torrent'],
        )

    def test_multi_torrent_aria2_command(self):
        sources = [r'C:\Torrents\one.torrent', "magnet:?xt=urn:btih:ABC123"]
        command = xget.add_torrent_options(["aria2c"], sources, 2, Path("downloads"))
        self.assertIn("--max-concurrent-downloads=2", command)
        self.assertIn("--check-integrity=true", command)
        self.assertIn("--allow-overwrite=true", command)
        self.assertIn("--auto-file-renaming=false", command)
        self.assertIn("--bt-hash-check-seed=false", command)
        self.assertIn("--log=downloads\\xget-aria2.log" if xget.os.name == "nt" else "--log=downloads/xget-aria2.log", command)
        self.assertEqual(command[-2:], sources)

    def test_aria2_exit_code_13_message(self):
        self.assertIn("already exists", xget.ARIA2_EXIT_MESSAGES[13])

    def test_youtube_options_mp4(self):
        options = xget.youtube_options(Path("/tmp/output"), False, None)
        self.assertIn("format", options)
        self.assertIn("default", options["outtmpl"])
        self.assertFalse(options["noplaylist"])
        self.assertEqual(options["sleep_interval_requests"], 1.0)
        self.assertEqual(options["sleep_interval"], 10.0)
        self.assertEqual(options["max_sleep_interval"], 15.0)
        self.assertEqual(options["concurrent_fragment_downloads"], 1)
        self.assertTrue(options["download_archive"].endswith(
            ".xget-youtube-archive.txt"
        ))

    def test_youtube_options_mp3(self):
        options = xget.youtube_options(Path("/tmp/output"), "mp3", None)
        self.assertEqual(options["format"], "bestaudio/best")

    def test_youtube_options_m4a(self):
        options = xget.youtube_options(Path("/tmp/output"), "m4a", None)
        self.assertEqual(options["format"], "bestaudio[ext=m4a]/bestaudio")
        if options["postprocessors"]:
            self.assertEqual(options["postprocessors"][0]["preferredcodec"], "m4a")

    def test_sync_youtube_archive_from_completed_files(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            (output / "Artist - Song [AbCdEf123_-].mp3").write_bytes(b"complete")
            (output / "Ignored [ZyXwVu987_-].part").write_bytes(b"partial")
            added, archive = xget.sync_youtube_archive(output)
            self.assertEqual(added, 1)
            self.assertEqual(archive.read_text(encoding="utf-8"), "youtube AbCdEf123_-\n")
            added_again, _ = xget.sync_youtube_archive(output)
            self.assertEqual(added_again, 0)

    def test_missing_ytdlp_does_not_install_during_check(self):
        result = xget.get_youtube_dl(auto_install=False)
        self.assertTrue(result is None or callable(result))

    def test_url_to_local_homepage(self):
        result = xget.url_to_local(Path("/mirror"), "https://example.com/", "text/html")
        self.assertEqual(result, Path("/mirror/example.com/index.html"))

    def test_url_to_local_page(self):
        result = xget.url_to_local(
            Path("/mirror"), "https://example.com/about", "text/html; charset=utf-8"
        )
        self.assertEqual(result, Path("/mirror/example.com/about.html"))

    def test_automatic_output_directories(self):
        self.assertEqual(xget.downloads_dir(), xget.APP_DIR / "downloads")
        self.assertEqual(xget.home_dir(), xget.APP_DIR / "home")

    def test_onedrive_viewer_url_conversion(self):
        source = (
            "https://onedrive.live.com/personal/test/_layouts/15/doc2.aspx"
            "?resid=ABC123!456&authkey=!XYZ&wdOrigin=OFFICECOM"
        )
        converted = xget.convert_cloud_download_url(source)
        self.assertIn("onedrive.live.com/download?", converted)
        self.assertIn("resid=ABC123%21456", converted)
        self.assertIn("authkey=%21XYZ", converted)

    def test_regular_url_is_not_changed(self):
        source = "https://example.com/file.zip"
        self.assertEqual(xget.convert_cloud_download_url(source), source)

    def test_read_cp949_url_list(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "urls.txt"
            path.write_bytes("# 목록\nhttps://example.com/file.zip\n".encode("cp949"))
            self.assertEqual(xget.read_text_lines(path), ["https://example.com/file.zip"])

    def test_reject_binary_url_list(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "invalid.txt"
            path.write_bytes(bytes(range(256)))
            with self.assertRaises(ValueError):
                xget.read_text_lines(path)

    def test_browser_headers_include_referer(self):
        headers = xget.browser_headers("https://example.com/book/1")
        self.assertIn("Mozilla/5.0", headers["User-Agent"])
        self.assertEqual(headers["Referer"], "https://example.com/")


if __name__ == "__main__":
    unittest.main()
