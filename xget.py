#!/usr/bin/env python3
"""xGet - terminal download menu for Windows and Ubuntu."""

from __future__ import annotations

import argparse
import glob
import hashlib
import os
import posixpath
import re
import shutil
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import deque
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlencode, urljoin, urlparse, urlunparse


APP_NAME = "xGet"
VERSION = "2.9.0"
HTTP_RE = re.compile(r"^https?://", re.IGNORECASE)
MAGNET_RE = re.compile(r"^magnet:\?xt=urn:", re.IGNORECASE)
APP_DIR = Path(__file__).resolve().parent
ARIA2_EXIT_MESSAGES = {
    3: "The requested resource was not found.",
    6: "A network error occurred.",
    7: "Downloads were unfinished when aria2 stopped.",
    9: "There is not enough free disk space.",
    11: "The same file is already being downloaded.",
    12: "The same Torrent info hash is already active.",
    13: "A destination file already exists.",
    14: "aria2 could not rename a file.",
    15: "aria2 could not open an existing file.",
    16: "aria2 could not create or truncate a file.",
    17: "A file I/O error occurred.",
    18: "aria2 could not create a directory.",
    25: "aria2 could not parse the .torrent file.",
    26: "The .torrent file is corrupt or missing required information.",
    27: "The Magnet URI is invalid.",
    28: "An aria2 option or option value is invalid.",
    32: "Checksum validation failed.",
}


def clear() -> None:
    os.system("cls" if os.name == "nt" else "clear")


def pause() -> None:
    input("\nPress Enter to return to the menu...")


def tool_path(name: str) -> str | None:
    found = shutil.which(name) or (shutil.which(f"{name}.exe") if os.name == "nt" else None)
    if found or os.name != "nt":
        return found
    if name.lower() == "aria2c":
        local_app_data = os.environ.get("LOCALAPPDATA")
        if local_app_data:
            package_root = Path(local_app_data) / "Microsoft" / "WinGet" / "Packages"
            if package_root.is_dir():
                candidates = list(package_root.glob("aria2.aria2_*/*/aria2c.exe"))
                candidates += list(package_root.glob("aria2.aria2_*/aria2c.exe"))
                for candidate in candidates:
                    if candidate.is_file():
                        return str(candidate)
    return None


def require_tool(name: str, purpose: str) -> str | None:
    path = tool_path(name)
    if not path:
        print(f"\n[ERROR] '{name}' is required for {purpose}, but it was not found.")
        print("Run the installer again or see the installation instructions in README.md.")
    return path


def get_youtube_dl(auto_install: bool = True):
    """Import yt_dlp and repair a missing installation in the active Python."""
    try:
        from yt_dlp import YoutubeDL

        return YoutubeDL
    except ImportError:
        if not auto_install:
            return None

    print("\n[INSTALL] The 'yt_dlp' module is missing. Installing it automatically.")
    print(f"[Python] {sys.executable}")
    try:
        command = [
            sys.executable,
            "-m",
            "pip",
            "install",
            "--upgrade",
            "yt-dlp",
        ]
        result = subprocess.run(command, check=False)
        if result.returncode != 0:
            print(f"\n[ERROR] Automatic yt_dlp installation failed. Exit code: {result.returncode}")
            print("Check your internet connection and run install_windows.ps1 again.")
            return None
        from yt_dlp import YoutubeDL

        print("[DONE] yt_dlp was installed successfully.")
        return YoutubeDL
    except (ImportError, OSError) as exc:
        print(f"\n[ERROR] Could not install or load yt_dlp: {exc}")
        return None


def ensure_web_modules():
    """Load the internal web-clone dependencies and repair them if missing."""
    try:
        import requests
        from bs4 import BeautifulSoup

        return requests, BeautifulSoup
    except ImportError:
        print("\n[INSTALL] Website mirror modules are missing. Installing them automatically.")
    try:
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "pip",
                "install",
                "--upgrade",
                "requests",
                "beautifulsoup4",
            ],
            check=False,
        )
        if result.returncode != 0:
            print(f"[ERROR] Website mirror module installation failed. Exit code: {result.returncode}")
            return None
        import requests
        from bs4 import BeautifulSoup

        return requests, BeautifulSoup
    except (ImportError, OSError) as exc:
        print(f"[ERROR] Could not prepare the website mirror modules: {exc}")
        return None


def run(command: list[str], cwd: Path | None = None) -> bool:
    print("\nCommand:")
    print(" ".join(f'"{part}"' if " " in part else part for part in command))
    print()
    try:
        result = subprocess.run(command, cwd=str(cwd) if cwd else None, check=False)
        if result.returncode == 0:
            print("\n[DONE] The operation completed successfully.")
            return True
        print(f"\n[FAILED] Process exit code: {result.returncode}")
        executable = Path(command[0]).name.lower()
        if executable in {"aria2c", "aria2c.exe"}:
            meaning = ARIA2_EXIT_MESSAGES.get(result.returncode)
            if meaning:
                print(f"[ARIA2] {meaning}")
        return False
    except KeyboardInterrupt:
        print("\n[STOPPED] The operation was cancelled by the user.")
        return False
    except OSError as exc:
        print(f"\n[ERROR] Could not run the command: {exc}")
        return False


def ask(prompt: str, default: str | None = None) -> str:
    suffix = f" [{default}]" if default else ""
    value = input(f"{prompt}{suffix}: ").strip()
    return value or (default or "")


def choose_file(title: str, filetypes: list[tuple[str, str]]) -> str:
    """Open the native file picker, with terminal input as a fallback."""
    try:
        import tkinter as tk
        from tkinter import filedialog

        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        selected = filedialog.askopenfilename(title=title, filetypes=filetypes)
        root.destroy()
        if selected:
            print(f"Selected file: {selected}")
            return selected
        print("[CANCELLED] No file was selected.")
        return ""
    except Exception as exc:
        print(f"[INFO] The graphical file picker is unavailable: {exc}")
        return ask("Enter the complete file path")


def choose_files(title: str, filetypes: list[tuple[str, str]]) -> list[str]:
    """Open a focused native multi-file picker, with terminal fallback."""
    root = None
    try:
        import tkinter as tk
        from tkinter import filedialog

        root = tk.Tk()
        root.title(title)
        root.geometry("1x1+0+0")
        root.overrideredirect(True)
        root.attributes("-topmost", True)
        root.update_idletasks()
        root.lift()
        root.focus_force()
        selected = filedialog.askopenfilenames(
            parent=root,
            title=title,
            filetypes=filetypes,
        )
        if selected:
            paths = [str(path) for path in selected]
            print(f"Selected files: {len(paths)}")
            return paths
        print("[CANCELLED] No file was selected.")
        return []
    except Exception as exc:
        print(f"[INFO] The graphical file picker is unavailable: {exc}")
        return read_sources_from_keyboard("Torrent file path")
    finally:
        if root is not None:
            try:
                root.destroy()
            except Exception:
                pass


def read_sources_from_keyboard(label: str) -> list[str]:
    """Read one or more paths/URLs without relying on a graphical dialog."""
    print(f"\nEnter one {label} per line. Submit a blank line when finished.")
    sources: list[str] = []
    while True:
        value = ask(f"{label} {len(sources) + 1}")
        if not value:
            break
        sources.append(value.strip().strip('"'))
    return sources


def app_output_dir(name: str) -> Path:
    path = APP_DIR / name
    path.mkdir(parents=True, exist_ok=True)
    print(f"Destination: {path}")
    return path


def downloads_dir() -> Path:
    return app_output_dir("downloads")


def home_dir() -> Path:
    return app_output_dir("home")


def valid_http_url(url: str) -> bool:
    if not HTTP_RE.match(url):
        return False
    parsed = urlparse(url)
    return bool(parsed.netloc)


def read_text_lines(path: Path) -> list[str]:
    """Read a text list using common Windows and Unicode encodings."""
    data = path.read_bytes()
    encodings = ("utf-16", "utf-8-sig", "cp949") if data.startswith((b"\xff\xfe", b"\xfe\xff")) else ("utf-8-sig", "cp949")
    for encoding in encodings:
        try:
            text = data.decode(encoding)
            return [
                line.strip()
                for line in text.splitlines()
                if line.strip() and not line.lstrip().startswith("#")
            ]
        except UnicodeDecodeError:
            continue
    raise ValueError(
        "The selected file is not a supported text URL list. "
        "Use UTF-8, UTF-16, or CP949 text."
    )


def aria2_base(output: Path) -> list[str] | None:
    aria2 = require_tool("aria2c", "Torrent and Magnet downloads")
    if not aria2:
        return None
    return [
        aria2,
        "--dir",
        str(output),
        "--continue=true",
        "--max-connection-per-server=8",
        "--split=8",
        "--min-split-size=1M",
        "--file-allocation=none",
        "--auto-file-renaming=true",
        "--console-log-level=notice",
        "--summary-interval=1",
    ]


def add_torrent_options(
    command: list[str], sources: list[str], concurrent: int, output: Path | None = None
) -> list[str]:
    """Return one aria2 command that schedules multiple Torrent jobs."""
    torrent_options = [
        "--seed-time=0",
        "--bt-enable-lpd=true",
        "--enable-dht=true",
        "--enable-peer-exchange=true",
        # Existing files are validated against Torrent piece hashes. Complete
        # files are kept; incomplete/corrupt data is repaired or downloaded.
        "--check-integrity=true",
        "--allow-overwrite=true",
        "--auto-file-renaming=false",
        "--bt-hash-check-seed=false",
        f"--max-concurrent-downloads={concurrent}",
    ]
    if output is not None:
        torrent_options.extend([
            f"--log={output / 'xget-aria2.log'}",
            "--log-level=notice",
        ])
    return command + torrent_options + sources


def convert_cloud_download_url(url: str) -> str:
    """Convert supported cloud-viewer URLs into direct-download URLs."""
    parsed = urlparse(url)
    query = parse_qs(parsed.query)
    if parsed.netloc.lower().endswith("onedrive.live.com"):
        resid = next((v[0] for k, v in query.items() if k.lower() == "resid" and v), "")
        authkey = next((v[0] for k, v in query.items() if k.lower() == "authkey" and v), "")
        if resid:
            direct_query = {"resid": resid}
            if authkey:
                direct_query["authkey"] = authkey
            return f"https://onedrive.live.com/download?{urlencode(direct_query)}"
    return url


def response_filename(response, requested_url: str) -> str:
    disposition = response.headers.get("content-disposition", "")
    utf_match = re.search(r"filename\*=UTF-8''([^;]+)", disposition, re.IGNORECASE)
    plain_match = re.search(r'filename="?([^";]+)"?', disposition, re.IGNORECASE)
    if utf_match:
        name = unquote(utf_match.group(1))
    elif plain_match:
        name = plain_match.group(1).strip()
    else:
        name = unquote(Path(urlparse(response.url or requested_url).path).name)
    name = safe_segment(name or "download.bin")
    if name.lower() in ("download", "doc2.aspx", "view.aspx"):
        name = "download.bin"
    return name


def format_bytes(value: int) -> str:
    amount = float(value)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if amount < 1024 or unit == "TB":
            return f"{amount:.1f} {unit}"
        amount /= 1024
    return f"{amount:.1f} TB"


def browser_headers(url: str) -> dict[str, str]:
    parsed = urlparse(url)
    origin = f"{parsed.scheme}://{parsed.netloc}/"
    return {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/131.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,"
        "image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Cache-Control": "no-cache",
        "Referer": origin,
        "Upgrade-Insecure-Requests": "1",
    }


def open_http_response(session, url: str):
    """Request a URL and retry a 403 once after establishing a site session."""
    headers = browser_headers(url)
    response = session.get(
        url,
        stream=True,
        timeout=(20, 120),
        allow_redirects=True,
        headers=headers,
    )
    if response.status_code != 403:
        return response
    response.close()
    parsed = urlparse(url)
    home = f"{parsed.scheme}://{parsed.netloc}/"
    try:
        landing = session.get(home, timeout=(20, 30), headers=browser_headers(home))
        landing.close()
    except Exception:
        pass
    return session.get(
        url,
        stream=True,
        timeout=(20, 120),
        allow_redirects=True,
        headers=browser_headers(url),
    )


def download_http_file(url: str, output: Path) -> tuple[bool, str]:
    modules = ensure_web_modules()
    if not modules:
        return False, "The HTTP download modules are unavailable."
    requests, _ = modules
    requested_url = convert_cloud_download_url(url)
    try:
        session = requests.Session()
        with open_http_response(session, requested_url) as response:
            if response.status_code == 403:
                return False, (
                    "403 Forbidden after a browser-style retry. The website may require "
                    "sign-in or may block automated downloads. Open the page in a browser "
                    "and use its public file-download link."
                )
            response.raise_for_status()
            content_type = response.headers.get("content-type", "").lower()
            filename = response_filename(response, requested_url)
            if "text/html" in content_type and not Path(filename).suffix:
                filename += ".html"
            elif "text/html" in content_type and filename == "download.bin":
                filename = "index.html"
            target = output / filename
            part = target.with_name(target.name + ".part")
            total = int(response.headers.get("content-length", "0") or 0)
            downloaded = 0
            with part.open("wb") as stream:
                for chunk in response.iter_content(chunk_size=1024 * 256):
                    if not chunk:
                        continue
                    stream.write(chunk)
                    downloaded += len(chunk)
                    if total:
                        percent = downloaded * 100 / total
                        status = (
                            f"\rDownloading {filename}: {percent:6.2f}% "
                            f"({format_bytes(downloaded)} / {format_bytes(total)})"
                        )
                    else:
                        status = f"\rDownloading {filename}: {format_bytes(downloaded)}"
                    print(status, end="", flush=True)
            print()
            if target.exists():
                stem, suffix = target.stem, target.suffix
                index = 1
                while target.exists():
                    target = output / f"{stem} ({index}){suffix}"
                    index += 1
            part.replace(target)
            if "text/html" in content_type:
                return True, f"Web page saved as HTML: {target}. Use menu 3 for a full mirror."
            return True, str(target)
    except KeyboardInterrupt:
        print()
        return False, "Download interrupted. The .part file was kept."
    except Exception as exc:
        print()
        return False, str(exc)


def direct_download() -> None:
    url = ask("Direct HTTP/HTTPS file or public sharing URL")
    if not valid_http_url(url):
        print("[ERROR] Enter a valid HTTP/HTTPS URL.")
        return
    success, message = download_http_file(url, downloads_dir())
    print(f"[{'DONE' if success else 'FAILED'}] {message}")


def url_list_download() -> None:
    raw = choose_file(
        "Select a URL list or Torrent file",
        [
            ("URL lists", "*.txt"),
            ("Torrent files", "*.torrent"),
            ("All files", "*.*"),
        ],
    )
    if not raw:
        return
    list_path = Path(raw).expanduser().resolve()
    if not list_path.is_file():
        print("[ERROR] The URL list file was not found.")
        return
    if list_path.suffix.lower() == ".torrent":
        print("[INFO] Torrent file detected. Opening the Torrent downloader.")
        torrent_download(str(list_path))
        return
    try:
        urls = read_text_lines(list_path)
    except (OSError, ValueError) as exc:
        print(f"[ERROR] {exc}")
        return
    if not urls:
        print("[ERROR] The selected URL list is empty.")
        return
    batch_http_download(urls, downloads_dir())


def batch_http_download(urls: list[str], output: Path, session: Path | None = None) -> None:
    valid_urls = [url for url in urls if valid_http_url(url)]
    failed: list[str] = []
    for index, url in enumerate(valid_urls, 1):
        print(f"\n[{index}/{len(valid_urls)}] {url}")
        success, message = download_http_file(url, output)
        print(f"[{'DONE' if success else 'FAILED'}] {message}")
        if not success:
            failed.append(url)
    session_path = session or (output / "xget.session")
    if failed:
        session_path.write_text("\n".join(failed) + "\n", encoding="utf-8")
        print(f"\nFailed URLs were saved to: {session_path}")
    elif session_path.exists():
        session_path.unlink()
    print(f"\nBatch result: {len(valid_urls) - len(failed)} succeeded / {len(failed)} failed")


def clean_url(url: str) -> str:
    parsed = urlparse(url)
    return urlunparse((parsed.scheme, parsed.netloc, parsed.path or "/", "", parsed.query, ""))


def safe_segment(value: str) -> str:
    value = unquote(value).strip().replace("\\", "_")
    value = re.sub(r'[<>:"|?*\x00-\x1f]', "_", value)
    return value[:120] or "_"


def url_to_local(root: Path, url: str, content_type: str = "") -> Path:
    parsed = urlparse(url)
    host = safe_segment(parsed.netloc.replace(":", "_"))
    parts = [safe_segment(item) for item in parsed.path.split("/") if item not in ("", ".", "..")]
    trailing_dir = parsed.path.endswith("/") or not parts
    suffix = Path(parts[-1]).suffix.lower() if parts else ""
    html_type = "text/html" in content_type
    if trailing_dir:
        parts.append("index.html")
    elif html_type and suffix not in (".html", ".htm"):
        parts[-1] += ".html"
    if parsed.query:
        digest = hashlib.sha1(parsed.query.encode("utf-8")).hexdigest()[:8]
        item = Path(parts[-1])
        parts[-1] = f"{item.stem}-{digest}{item.suffix}"
    return root / host / Path(*parts)


def relative_link(from_file: Path, to_file: Path) -> str:
    return Path(os.path.relpath(to_file, from_file.parent)).as_posix()


def website_clone() -> None:
    modules = ensure_web_modules()
    if not modules:
        return
    requests, BeautifulSoup = modules
    start_url = ask("Web page or website URL to mirror")
    if not valid_http_url(start_url):
        print("[ERROR] Enter a valid HTTP/HTTPS URL.")
        return
    start_url = clean_url(start_url)
    output = home_dir()
    parsed_start = urlparse(start_url)
    clone_root = output / f"{safe_segment(parsed_start.netloc)}-mirror"
    clone_root.mkdir(parents=True, exist_ok=True)
    print("\nMirror scope")
    print("  1. Mirror only pages below the entered path")
    print("  2. Mirror the entire website on the same domain (recommended)")
    whole_domain = ask("Select", "2") == "2"
    raw_limit = ask("Maximum number of HTML pages", "500")
    page_limit = max(1, min(5000, int(raw_limit) if raw_limit.isdigit() else 500))

    session = requests.Session()
    session.headers.update(browser_headers(start_url))
    queue = deque([start_url])
    visited_pages: set[str] = set()
    downloaded: dict[str, Path] = {}
    failures: list[tuple[str, str]] = []

    def allowed_page(url: str) -> bool:
        parsed = urlparse(url)
        if parsed.netloc != parsed_start.netloc:
            return False
        if whole_domain:
            return True
        base = posixpath.dirname(parsed_start.path.rstrip("/")) or "/"
        return parsed.path.startswith(base)

    def fetch_asset(asset_url: str) -> Path | None:
        asset_url = clean_url(asset_url)
        if asset_url in downloaded:
            return downloaded[asset_url]
        try:
            response = session.get(asset_url, timeout=30)
            response.raise_for_status()
            content_type = response.headers.get("content-type", "")
            target = url_to_local(clone_root, asset_url, content_type)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(response.content)
            downloaded[asset_url] = target
            print(f"  [FILE] {asset_url}")
            return target
        except Exception as exc:
            failures.append((asset_url, str(exc)))
            return None

    while queue and len(visited_pages) < page_limit:
        page_url = clean_url(queue.popleft())
        if page_url in visited_pages:
            continue
        visited_pages.add(page_url)
        try:
            response = session.get(page_url, timeout=30)
            response.raise_for_status()
            content_type = response.headers.get("content-type", "")
            if "text/html" not in content_type:
                fetch_asset(page_url)
                continue
            page_file = url_to_local(clone_root, page_url, content_type)
            downloaded[page_url] = page_file
            soup = BeautifulSoup(response.content, "html.parser")

            for tag, attribute in (
                ("img", "src"),
                ("script", "src"),
                ("link", "href"),
                ("source", "src"),
                ("video", "poster"),
            ):
                for node in soup.find_all(tag):
                    raw = node.get(attribute)
                    if not raw or raw.startswith(("data:", "javascript:", "mailto:", "#")):
                        continue
                    absolute = clean_url(urljoin(page_url, raw))
                    if not valid_http_url(absolute):
                        continue
                    asset_file = fetch_asset(absolute)
                    if asset_file:
                        node[attribute] = relative_link(page_file, asset_file)

            for anchor in soup.find_all("a", href=True):
                raw = anchor.get("href", "")
                if raw.startswith(("javascript:", "mailto:", "tel:", "#")):
                    continue
                absolute = clean_url(urljoin(page_url, raw))
                if not valid_http_url(absolute) or not allowed_page(absolute):
                    continue
                queue.append(absolute)
                destination = url_to_local(clone_root, absolute, "text/html")
                anchor["href"] = relative_link(page_file, destination)

            page_file.parent.mkdir(parents=True, exist_ok=True)
            page_file.write_text(str(soup), encoding="utf-8")
            print(f"[PAGE {len(visited_pages)}/{page_limit}] {page_url}")
        except Exception as exc:
            failures.append((page_url, str(exc)))
            print(f"[FAILED] {page_url}: {exc}")

    print("\n" + "=" * 64)
    print(f"[DONE] HTML pages: {len(visited_pages)}, total saved files: {len(downloaded)}")
    print(f"Destination: {clone_root}")
    if failures:
        print(f"Failed URLs: {len(failures)}")


def read_youtube_urls() -> list[str]:
    print("\nYou can enter multiple URLs separated by commas or spaces.")
    print("Press Enter without typing a URL to use multi-line input mode.")
    first = ask("YouTube URL")
    raw_lines: list[str] = []
    if first:
        raw_lines.append(first)
    else:
        print("\nEnter one URL per line. Submit a blank line when finished.")
        index = 1
        while True:
            line = ask(f"URL {index}")
            if not line:
                break
            raw_lines.append(line)
            index += 1

    candidates = re.split(r"[,\s]+", "\n".join(raw_lines).strip())
    urls = [
        value
        for value in candidates
        if value and valid_http_url(value)
        and ("youtube.com" in value.lower() or "youtu.be" in value.lower())
    ]
    rejected = len([value for value in candidates if value]) - len(urls)
    if rejected:
        print(f"[INFO] Ignored {rejected} item(s) that were not valid YouTube URLs.")
    return list(dict.fromkeys(urls))


def youtube_options(
    output: Path, audio_format: str | None, cookie_file: Path | None
) -> dict:
    ffmpeg_available = bool(tool_path("ffmpeg"))
    if audio_format:
        postprocessors = []
        if ffmpeg_available:
            postprocessors = [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": audio_format,
                **({"preferredquality": "192"} if audio_format == "mp3" else {}),
            }]
        format_selector = (
            "bestaudio[ext=m4a]/bestaudio" if audio_format == "m4a"
            else "bestaudio/best"
        )
    else:
        postprocessors = []
        format_selector = (
            "bestvideo[height<=1080]+bestaudio/"
            "best[height<=1080]/best"
            if ffmpeg_available
            else "best[ext=mp4]/best"
        )

    options = {
        "format": format_selector,
        "outtmpl": {
            "default": str(output / "%(title).180B [%(id)s].%(ext)s"),
            "playlist": str(
                output / "%(playlist_title).120B"
                / "%(playlist_index)03d-%(title).150B [%(id)s].%(ext)s"
            ),
        },
        "ignoreerrors": True,
        "continuedl": True,
        "nopart": False,
        # YouTube commonly rate-limits guest sessions after a few hundred
        # videos per hour. Pace extraction and downloads instead of retrying
        # aggressively. The randomized per-video delay is recommended by
        # yt-dlp for large playlists.
        "sleep_interval_requests": 1.0,
        "sleep_interval": 10.0,
        "max_sleep_interval": 15.0,
        "retries": 10,
        "fragment_retries": 10,
        "extractor_retries": 3,
        "concurrent_fragment_downloads": 1,
        # Completed video IDs are recorded so restarting a large playlist
        # skips successful items and continues from the remaining entries.
        "download_archive": str(output / ".xget-youtube-archive.txt"),
        "windowsfilenames": True,
        "noplaylist": False,
        "writethumbnail": False,
        "writesubtitles": False,
        "postprocessors": postprocessors,
        "quiet": False,
        "no_warnings": False,
    }
    if not audio_format and ffmpeg_available:
        options["merge_output_format"] = "mp4"
    if cookie_file and cookie_file.is_file():
        options["cookiefile"] = str(cookie_file)
    return options


def sync_youtube_archive(output: Path) -> tuple[int, Path]:
    """Add IDs found in completed filenames to yt-dlp's download archive."""
    archive = output / ".xget-youtube-archive.txt"
    existing: set[str] = set()
    if archive.is_file():
        existing = {
            line.strip()
            for line in archive.read_text(encoding="utf-8", errors="ignore").splitlines()
            if line.strip()
        }

    completed_extensions = {".mp3", ".m4a", ".mp4", ".mkv", ".opus", ".webm"}
    found: set[str] = set()
    for path in output.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in completed_extensions:
            continue
        for video_id in re.findall(r"\[([A-Za-z0-9_-]{11})\]", path.name):
            found.add(f"youtube {video_id}")

    additions = sorted(found - existing)
    if additions:
        archive.parent.mkdir(parents=True, exist_ok=True)
        with archive.open("a", encoding="utf-8", newline="\n") as handle:
            if archive.stat().st_size and not archive.read_bytes().endswith(b"\n"):
                handle.write("\n")
            handle.write("\n".join(additions) + "\n")
    return len(additions), archive


def download_one_youtube(
    url: str,
    output: Path,
    audio_format: str | None,
    cookie_file: Path | None,
    worker: int,
) -> tuple[str, bool, str]:
    YoutubeDL = get_youtube_dl()
    if not YoutubeDL:
        return url, False, "The yt_dlp module is not installed."
    print(f"\n[JOB {worker}] Starting download: {url}")
    try:
        with YoutubeDL(youtube_options(output, audio_format, cookie_file)) as ydl:
            error_code = ydl.download([url])
        if error_code == 0:
            return url, True, "Completed"
        return url, False, f"yt-dlp exit code {error_code}"
    except Exception as exc:
        return url, False, str(exc)


def youtube_download() -> None:
    if not get_youtube_dl():
        return
    urls = read_youtube_urls()
    if not urls:
        print("[ERROR] No valid YouTube URL was entered.")
        return
    output = downloads_dir()

    print("\nDownload format")
    print("  1. MP4 video (up to 1080p)")
    print("  2. M4A audio (default)")
    print("  3. MP3 audio")
    mode = ask("Select", "2")
    audio_format = {"2": "m4a", "3": "mp3"}.get(mode)

    cookie_default = Path(__file__).resolve().parent / "cookies.txt"
    cookie_file: Path | None = cookie_default if cookie_default.is_file() else None
    if cookie_file:
        print(f"[INFO] Using cookies.txt: {cookie_file}")

    archived_count, archive_path = sync_youtube_archive(output)
    if archived_count:
        print(f"[INFO] Added {archived_count} existing download(s) to the resume archive.")
    print(f"[INFO] Resume archive: {archive_path}")

    workers = 1
    if len(urls) > 1:
        raw_workers = ask("Concurrent downloads (1-2; 1 recommended)", "1")
        workers = max(1, min(2, int(raw_workers) if raw_workers.isdigit() else 1))
        if workers > 1:
            print("[WARNING] Concurrent YouTube jobs increase the rate-limit risk.")

    print(f"\nTotal URLs: {len(urls)} / Concurrent jobs: {workers}")
    print(f"Destination: {output}")
    print("Safe pacing: 1 second between extraction requests and 10-15 seconds per video")
    results: list[tuple[str, bool, str]] = []
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {
            executor.submit(
                download_one_youtube,
                url,
                output,
                audio_format,
                cookie_file,
                index,
            ): url
            for index, url in enumerate(urls, 1)
        }
        for future in as_completed(futures):
            results.append(future.result())

    success = sum(1 for _, ok, _ in results if ok)
    print("\n" + "=" * 64)
    print(f"Download results: {success} succeeded / {len(results) - success} failed")
    for url, ok, message in results:
        print(f"  {'[SUCCESS]' if ok else '[FAILED]'} {url}")
        if not ok:
            print(f"         {message}")


def cleanup_incomplete() -> None:
    target = downloads_dir()
    if not target.is_dir():
        print("[ERROR] The directory was not found.")
        return
    patterns = ("*.part", "*.ytdl", "*.temp", "*.part-Frag*", "*.aria2")
    matches: list[Path] = []
    for pattern in patterns:
        matches.extend(Path(item) for item in glob.glob(str(target / "**" / pattern), recursive=True))
    unique_files = sorted({path for path in matches if path.is_file()})
    if not unique_files:
        print("[DONE] No incomplete download files were found.")
        return
    print(f"\nFound {len(unique_files)} incomplete file(s).")
    if ask("Delete these files? (y/N)", "N").lower() != "y":
        print("[CANCELLED] No files were deleted.")
        return
    deleted = 0
    for path in unique_files:
        try:
            path.unlink()
            deleted += 1
            print(f"Deleted: {path}")
        except OSError as exc:
            print(f"Delete failed: {path} ({exc})")
    print(f"[DONE] Deleted {deleted} file(s).")


def torrent_download(selected_source: str | None = None) -> None:
    if selected_source:
        sources = [selected_source]
    else:
        print("\nTorrent source")
        print("  1. Enter Magnet URL(s) with the keyboard")
        print("  2. Enter .torrent file path(s) with the keyboard")
        print("  3. Select one or more .torrent files in a file window")
        source_type = ask("Select", "2")
        if source_type == "1":
            sources = read_sources_from_keyboard("Magnet URL")
        elif source_type == "2":
            sources = read_sources_from_keyboard("Torrent file path")
        else:
            sources = choose_files(
                "Select Torrent files (Ctrl/Shift selects multiple)",
                [("Torrent files", "*.torrent"), ("All files", "*.*")],
            )
    if not sources:
        print("[CANCELLED] No Torrent or Magnet source was entered.")
        return

    resolved_sources: list[str] = []
    for source in dict.fromkeys(sources):
        if MAGNET_RE.match(source):
            resolved_sources.append(source)
            continue
        torrent_path = Path(source).expanduser()
        if torrent_path.is_file() and torrent_path.suffix.lower() == ".torrent":
            resolved_sources.append(str(torrent_path.resolve()))
        else:
            print(f"[WARNING] Ignored invalid Torrent source: {source}")
    if not resolved_sources:
        print("[ERROR] No valid Magnet URL or .torrent file remains.")
        return

    concurrent_default = str(min(3, len(resolved_sources)))
    concurrent_raw = ask("Concurrent Torrent jobs (1-10)", concurrent_default)
    concurrent = max(
        1,
        min(10, int(concurrent_raw) if concurrent_raw.isdigit() else int(concurrent_default)),
    )
    output = downloads_dir()
    command = aria2_base(output)
    if not command:
        return
    command = add_torrent_options(command, resolved_sources, concurrent, output)
    print(f"[INFO] Torrent sources: {len(resolved_sources)} / Concurrent jobs: {concurrent}")
    print("[INFO] Existing files will be hash-checked; only missing or damaged data is downloaded.")
    print(f"[INFO] aria2 log: {output / 'xget-aria2.log'}")
    run(command)


def resume_session() -> None:
    raw = choose_file(
        "Select an xGet session file",
        [
            ("xGet session", "xget.session"),
            ("Session files", "*.session"),
            ("Torrent files", "*.torrent"),
            ("All files", "*.*"),
        ],
    )
    if not raw:
        return
    session = Path(raw).expanduser().resolve()
    if not session.is_file():
        print("[ERROR] The session file was not found.")
        return
    if session.suffix.lower() == ".torrent":
        print("[INFO] Torrent file detected. Opening the Torrent downloader.")
        torrent_download(str(session))
        return
    try:
        urls = read_text_lines(session)
    except (OSError, ValueError) as exc:
        print(f"[ERROR] {exc}")
        return
    if not urls:
        print("[ERROR] The selected session file is empty.")
        return
    batch_http_download(urls, downloads_dir(), session)


def diagnostics() -> None:
    print(f"\n{APP_NAME} {VERSION} dependency status")
    for name, purpose in (
        ("aria2c", "Torrent and Magnet downloads"),
        ("ffmpeg", "video and audio merging/conversion"),
    ):
        path = tool_path(name)
        print(f"  {'[OK]' if path else '[MISSING]'} {name:<8} {purpose}")
        if path:
            print(f"           {path}")
    try:
        import yt_dlp
        from yt_dlp.version import __version__ as ytdlp_version

        print(f"  [OK] yt_dlp   YouTube Python module ({ytdlp_version})")
    except (ImportError, AttributeError):
        print("  [MISSING] yt_dlp   YouTube Python module")
    try:
        import requests
        from bs4 import BeautifulSoup  # noqa: F401

        print(f"  [OK] requests  website mirror module ({requests.__version__})")
    except ImportError:
        print("  [MISSING] requests/bs4 website mirror modules")


def menu() -> int:
    actions = {
        "1": direct_download,
        "2": url_list_download,
        "3": website_clone,
        "4": youtube_download,
        "5": torrent_download,
        "6": resume_session,
        "7": diagnostics,
        "8": cleanup_incomplete,
    }
    while True:
        clear()
        print("=" * 64)
        print(f"  {APP_NAME} {VERSION} - Integrated Terminal Downloader")
        print("=" * 64)
        print("  1. Download a direct HTTP/HTTPS file")
        print("  2. Download files from a URL list")
        print("  3. Mirror a web page or website")
        print("  4. Download YouTube video or audio")
        print("  5. Download a Torrent or Magnet link")
        print("  6. Resume an interrupted URL-list download")
        print("  7. Check dependency status")
        print("  8. Clean incomplete download files")
        print("  0. Exit")
        print("=" * 64)
        choice = ask("Select a menu option")
        if choice == "0":
            return 0
        action = actions.get(choice)
        if not action:
            print("[ERROR] Select a valid menu number.")
        else:
            try:
                action()
            except KeyboardInterrupt:
                print("\n[STOPPED] The operation was cancelled by the user.")
            except Exception as exc:
                print(f"\n[ERROR] The operation could not be completed: {exc}")
        pause()


def main() -> int:
    parser = argparse.ArgumentParser(description="xGet terminal download manager")
    parser.add_argument("--version", action="version", version=f"%(prog)s {VERSION}")
    parser.add_argument("--check", action="store_true", help="check dependency status")
    args = parser.parse_args()
    if args.check:
        diagnostics()
        return 0
    return menu()


if __name__ == "__main__":
    raise SystemExit(main())
