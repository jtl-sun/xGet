import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

MODULE = Path(__file__).parents[1] / "xget.py"
SPEC = importlib.util.spec_from_file_location("xget_216", MODULE)
xget = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(xget)


def bencode(value):
    if isinstance(value, int):
        return b"i" + str(value).encode() + b"e"
    if isinstance(value, bytes):
        return str(len(value)).encode() + b":" + value
    if isinstance(value, dict):
        return b"d" + b"".join(bencode(k) + bencode(v) for k,v in sorted(value.items())) + b"e"
    raise TypeError(value)


class FakeResponse:
    def __init__(self, code=200, headers=None, chunks=(b"DATA",), url="https://example.org/package.zip"):
        self.status_code = code
        self.headers = headers or {"content-type":"application/zip", "etag":"\"abcd\"", "content-length":"4"}
        self.chunks = chunks
        self.url = url
    def close(self): pass
    def __enter__(self): return self
    def __exit__(self, *_): return False
    def raise_for_status(self):
        if self.status_code >= 400:
            raise xget.requests.exceptions.HTTPError(f"HTTP {self.status_code}")
    def iter_content(self, chunk_size=1):
        yield from self.chunks


class XGet216Tests(unittest.TestCase):
    def test_bittorrent_versions(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/"data.torrent"
            info = {b"name": b"test", b"pieces":b"a"*20}
            path.write_bytes(bencode({b"info":info}))
            self.assertEqual(xget.inspect_torrent_version(path), "v1")
            info[b"meta version"] = 2
            path.write_bytes(bencode({b"info":info}))
            self.assertEqual(xget.inspect_torrent_version(path), "hybrid")
            del info[b"pieces"]
            info[b"file tree"] = {}
            path.write_bytes(bencode({b"info":info}))
            self.assertEqual(xget.inspect_torrent_version(path), "v2")
            path.write_bytes(b"not a torrent")
            self.assertEqual(xget.inspect_torrent_version(path), "invalid")

    def test_magnet_version(self):
        self.assertEqual(xget.magnet_version("magnet:?xt=urn:btih:aaa"), "v1")
        self.assertEqual(xget.magnet_version("magnet:?xt=urn:btmh:1220aaa"), "v2")
        self.assertEqual(xget.magnet_version("magnet:?xt=urn:btmh:1220aaa&xt=urn:btih:bbb"), "hybrid")

    def test_v2_hand_off_does_not_mark_complete(self):
        with patch.object(xget, 'find_qbittorrent', return_value='/usr/bin/qbittorrent'), patch.object(xget.subprocess, 'Popen') as process:
            result = xget.handoff_to_qbittorrent(['magnet:?xt=urn:btmh:1220abc'], Path('/tmp/xget download'))
            self.assertTrue(result)
            args = process.call_args.args[0]
            self.assertEqual(args[1], '--save-path=/tmp/xget download')
            self.assertEqual(args[2], 'magnet:?xt=urn:btmh:1220abc')

    def test_no_aria2_v2_only(self):
        with patch.object(xget, 'ask', return_value='N'), patch.object(xget, 'aria2_base') as base:
            xget.torrent_download('magnet:?xt=urn:btmh:1220aa')
            base.assert_not_called()

    def test_html_installer_rejected(self):
        self.assertTrue(xget.unexpected_html_file('https://example.org/driver.exe','login.html', 'text/html'))
        self.assertFalse(xget.unexpected_html_file('https://example.org/index.html','index.html','text/html'))

    def test_retry_after_bounded(self):
        self.assertEqual(xget.http_retry_wait(FakeResponse(headers={'retry-after':'120'}), 0), 10)
        self.assertEqual(xget.http_retry_wait(FakeResponse(headers={}), 1), 2)

    def test_simple_download_and_resume(self):
        import requests
        class Session:
            def __init__(self): self.calls=[]
            def get(self, url, **kwargs):
                self.calls.append(kwargs)
                headers=kwargs.get('headers',{})
                if 'Range' in headers:
                    return FakeResponse(206, {"content-type":"application/zip", "etag":"\"abcd\"", "content-range":"bytes 2-3/4", "content-length":"2"}, (b'TA',))
                return FakeResponse()
        with tempfile.TemporaryDirectory() as directory:
            output=Path(directory)
            with patch.object(requests, 'Session', Session):
                result=xget.download_http_file('https://example.org/package.zip', output)
                self.assertTrue(result[0], result)
                self.assertEqual((output/'package.zip').read_bytes(), b'DATA')
                (output/'package.zip').unlink()
                (output/'package.zip.part').write_bytes(b'DA')
                (output/'package.zip.part.json').write_text(json.dumps({'url':'https://example.org/package.zip','filename':'package.zip','validator':'"abcd"'}))
                result=xget.download_http_file('https://example.org/package.zip', output)
                self.assertTrue(result[0], result)
                self.assertEqual((output/'package.zip').read_bytes(), b'DATA')
                self.assertFalse((output/'package.zip.part.json').exists())

    def test_reject_conflicting_resume_content_range(self):
        import requests
        class Session:
            def get(self, url, **kwargs):
                if 'Range' in kwargs.get('headers', {}):
                    return FakeResponse(206, {
                        'content-type': 'application/zip', 'etag': '"abcd"',
                        'content-range': 'bytes 2-3/5', 'content-length': '2',
                    }, (b'TA',))
                return FakeResponse()
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            (output/'package.zip.part').write_bytes(b'DA')
            (output/'package.zip.part.json').write_text(json.dumps({
                'url':'https://example.org/package.zip', 'filename':'package.zip',
                'validator':'"abcd"',
            }))
            with patch.object(requests, 'Session', Session):
                ok, message = xget.download_http_file('https://example.org/package.zip', output)
            self.assertFalse(ok)
            self.assertIn('Content-Range', message)
            self.assertEqual((output/'package.zip.part').read_bytes(), b'DA')
            self.assertFalse((output/'package.zip').exists())

    def test_html_disguised_as_archive_is_not_saved(self):
        import requests
        class Session:
            def get(self, url, **kwargs):
                return FakeResponse(200, {"content-type":"text/html", "content-length":"4"}, (b'HTML',))
        with tempfile.TemporaryDirectory() as directory:
            output=Path(directory)
            with patch.object(requests,'Session', Session):
                ok, message = xget.download_http_file('https://example.org/driver.zip', output)
            self.assertFalse(ok)
            self.assertIn('HTML', message)
            self.assertEqual(list(output.iterdir()), [])

if __name__ == '__main__': unittest.main()
