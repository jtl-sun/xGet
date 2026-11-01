# xGet 2.15.0

xGet is a menu-driven integrated terminal downloader for Windows and Ubuntu.

## Features

- Download a direct HTTP/HTTPS file
- Download supported public OneDrive sharing URLs
- Download multiple files from a TXT URL list
- Resume interrupted downloads
- Mirror a web page or an entire website on the same domain
- Download YouTube videos, playlists, channels, MP3 audio, and M4A audio
- Download multiple YouTube URLs concurrently, including playlists/channels and a TXT URL batch (prefix path with `@`)
- Automatically use a local `cookies.txt` file
- Clean incomplete download files
- Manually refresh Deno, yt-dlp Nightly, and EJS without changing cookies
- Download one or multiple `.torrent` files and Magnet links concurrently
- Preview files within a single `.torrent` and choose which indexes to download
- Save Torrent-only speed limits, seeding preferences, peer count, and concurrency
- Manually repair YouTube components; automatically repair missing website-mirror modules
- Mirror websites without a separate `wget.exe`
- Download direct files and URL lists without `aria2c`
- Select URL lists, session files, and Torrent files with the native file picker
- Detect a `.torrent` file selected from menu 2 or menu 6 and route it automatically
- Read URL-list text encoded as UTF-8, UTF-16, or CP949
- Keep the main menu running after an invalid file selection
- Retry HTTP 403 responses once with a browser-style session
- Save a successfully retrieved web page as HTML and recommend menu 3 for mirroring
- Show MP3 conversion start, live elapsed activity, item position, and completion
- Install on Windows by double-clicking `INSTALL-xGet.bat`
- Create a Desktop shortcut for one-click execution
- Choose and remember a custom download folder for HTTP, URL-list, YouTube, Torrent, and Magnet downloads
- Choose and remember a separate web-mirror folder
- Reset storage locations to the original xGet defaults at any time
- Show download percentages in bold green three-digit format when progress can be calculated

## File Picker

Menu 2 opens a file picker for selecting a URL-list TXT file. Menu 6 opens a
file picker for selecting `xget.session`. Menu 5 supports keyboard-only path or
Magnet entry and a focused multi-file picker. In the picker, use Ctrl/Shift to
select multiple `.torrent` files. If a graphical file picker is unavailable,
xGet falls back to terminal path input.

## Torrent Downloads

Menu 5 can receive multiple `.torrent` paths or Magnet URLs, one per line. It
then asks how many Torrent jobs (1-10) aria2 should run concurrently. aria2 also
downloads pieces from multiple peers inside each Torrent. Using too many jobs
can reduce overall speed or overload a router; 2-3 concurrent jobs is the
recommended starting point.

If destination files already exist, xGet asks aria2 to validate their Torrent
piece hashes. Complete files are preserved; missing or damaged data is fetched
again. Detailed aria2 diagnostics are appended to
`downloads/xget-aria2.log`. aria2 exit code 13 means that a destination file
already existed; xGet 2.8 includes integrity/overwrite options to handle this
case instead of silently failing.

## Torrent Controls (2.15.0)

Menu **5** previews the file list in a single local `.torrent` using aria2
`--show-files=true`. You can enter file indexes such as `1,3-5`, or press Enter
to fetch everything. This selective mode is available only for **one local
`.torrent` file at a time**. Multi-torrent and Magnet jobs still work; Magnet
metadata is saved when available, but selecting individual files directly from
a Magnet URL is not supported until you have a local `.torrent`. Because Torrent
pieces can span file boundaries, aria2 may write small portions of unselected
files. xGet does not automatically remove these.

Menu **11** saves Torrent-only options in `xget-settings.json`:

- Concurrent Torrent jobs (1-10, defaults to 3; never exceeds supplied job count)
- Overall Torrent download/upload speed limits (`0` is unlimited, e.g., `500K` or `2M`)
- Seeding time in minutes (`0` means stop seeding after completion, legacy behavior)
- Seeding ratio (default 1.0 when seeding is enabled)
- Maximum peers per Torrent (default 55)

The options apply to new aria2 Torrent/Magnet runs, not YouTube downloads.
Existing data is hash-checked. Stop with Ctrl+C and use the same source and
download folder to resume. Do not move or delete `.aria2` resume state files:
xGet now excludes them from menu 8 cleanup. aria2 remains a terminal downloader;
xGet does not claim to reproduce the complete qBittorrent/uTorrent GUI,
background task manager, or live queue reordering.

## Storage Locations

By default, xGet keeps the same storage layout used by earlier releases:

```text
xGet/
├── xget.py
├── downloads/   Direct files, URL lists, YouTube, Torrent, and Magnet downloads
└── home/        Mirrored web pages and websites
```

Use **menu 10 - Set storage locations** to choose a different folder. The
download folder and web-mirror folder can be configured separately. xGet saves
the selection in `xget-settings.json` and uses it on later runs. Changing a
location does **not** move or delete existing files. Resetting the setting
returns xGet to the default folders above.

The YouTube resume archive (`.xget-youtube-archive.txt`), URL-list session file,
and aria2 log are kept inside the currently selected download folder so resume
behavior follows the chosen destination. `cookies.txt` remains beside `xget.py`
and is not changed by storage settings.

## Windows Installation

1. Extract the ZIP file.
2. Double-click `INSTALL-xGet.bat`.
3. When installation finishes, double-click the **xGet** shortcut on the Desktop.

The BAT installer safely starts the PowerShell installer with a one-process
execution-policy bypass, so the red `PSSecurityException` shown when running a
PS1 file directly does not occur. You may also install from a terminal with:

```powershell
powershell -ExecutionPolicy Bypass -File .\install_windows.ps1
```

You may run xGet directly from the extracted folder by double-clicking
`RUN-xGet.bat`. After installation, a terminal command also works:

```powershell
xget
```

## Ubuntu Installation

```bash
chmod +x install_ubuntu.sh
./install_ubuntu.sh
xget
```

## Menu

```text
1. Download a direct HTTP/HTTPS file
2. Download files from a URL list
3. Mirror a web page or website
4. Download YouTube video or audio
5. Download a Torrent or Magnet link
6. Resume an interrupted URL-list download
7. Check dependency status
8. Clean incomplete download files
9. Refresh YouTube components (manual)
10. Set storage locations
11. Set Torrent preferences (limits, seeding, peers)
0. Exit
```

## Website Mirroring

xGet downloads HTML, images, CSS, JavaScript, and internal page links, then
rewrites supported links for local browsing. Content that requires login, DRM,
server-side processing, infinite scrolling, or complex JavaScript may not be
fully available offline.

Respect each website's terms of service and copyright requirements.

## YouTube Downloads

For a large **multi-file** batch, enter several YouTube URLs separated by
spaces/commas, use the multiline input mode, supply a playlist/channel URL,
or input `@/path/to/youtube-urls.txt` at the first URL prompt. Completed IDs
continue to be archived. The job scheduler starts only 1-2 URL tasks at once
and does not queue all URLs ahead of the five-error stop rule.

Use this feature only for content that you own or are authorized to download.
Keep `yt-dlp` current to accommodate YouTube changes.

The default YouTube download format is M4A audio. MP4 video and MP3 audio
remain available from the format menu. M4A is preferred directly from YouTube
and FFmpeg finalizes the file as M4A when conversion is required.

For direct HTTP downloads and YouTube transfers, xGet shows progress in bold
green three-digit form such as `007 %`, `054 %`, and `100 %`. If an HTTP server
does not provide a usable total size, xGet displays `--- %` rather than inventing
a percentage. When FFmpeg starts an MP3 conversion, xGet displays
`MP3 CONVERSION`, the playlist item number, live activity, and completion status
so a long conversion does not look like the program has stopped.

Large playlists run in fast mode with no artificial delay between extraction
requests or videos, and up to four media fragment connections. Five download
errors at any point automatically stop the remaining playlist so a temporary
service limit does not produce endless failures. Successful video IDs are saved in
`downloads/.xget-youtube-archive.txt`. If a run is interrupted or YouTube
temporarily rate-limits the session, run the same playlist again later; xGet
will skip recorded items and continue with the remainder.

The message `This content isn't available, try again later` accompanied by a
session rate-limit notice is a temporary YouTube request limit, not a local
file-count limit. Stop the run, wait for the period shown by YouTube (often up
to an hour), and then resume. Starting more simultaneous jobs while limited
usually prolongs the problem.

## Manual YouTube Refresh

If YouTube downloads repeatedly fail with HTTP 403 or JavaScript challenge
errors, select menu 9 and confirm the refresh. xGet updates Deno plus the
Nightly `yt-dlp[default]` package, which includes the matching EJS challenge
scripts. The refresh runs only when selected and confirmed. It does not modify
`cookies.txt`, downloaded media, or `.xget-youtube-archive.txt`.

Windows installations can be updated by running `install_windows.ps1` again.
Ubuntu installations can be updated by running `install_ubuntu.sh` again.

## Dependency Check

```text
xget --check
```

`ffmpeg`, `yt_dlp`, and the website mirror modules should display `[OK]`.
`aria2c` is required only for Torrent and Magnet downloads. Website mirroring
does not require `wget`.

## Public Cloud Sharing URLs

Menu 1 accepts direct HTTP/HTTPS file URLs. It also converts supported public
OneDrive document-viewer URLs containing a `resid` parameter into download
URLs. Private files may still require sign-in and cannot be downloaded without
authorization.

## Uninstallation

Windows:

```powershell
powershell -ExecutionPolicy Bypass -File .\uninstall_windows.ps1
```

Ubuntu:

```bash
chmod +x uninstall_ubuntu.sh
./uninstall_ubuntu.sh
```

## Important

- Follow the target website's terms, copyright restrictions, and local laws.
- Use Torrent support only for content that you own or may legally distribute.
- VPN management is not included. Use a separate trusted VPN application when required.

## 2.14.0 Ubuntu parity update (2026-10-02)

Windows and Ubuntu install the identical `xget.py`, with one runtime `VERSION`
constant. There is no separate Ubuntu core. Both report 2.14.0.

Extract `xGet-2.14.0-English.zip`, open a terminal in the extracted folder, and run:

```bash
bash ./install_ubuntu.sh
~/.local/bin/xget --version
~/.local/bin/xget
```

Expected version output: `xget.py 2.14.0`.
The installer replaces `~/.local/share/xget/xget.py` and the launcher, uses
`~/.local/share/xget/venv/bin/python`, upgrades `yt-dlp[default]`, checks EJS and
FFmpeg, installs a missing/unsupported Deno, and compares the launcher's version
with the source release. Deno must be at least 2.3.0, per the current upstream
EJS requirements: https://github.com/yt-dlp/yt-dlp/wiki/EJS .
No shell reload is needed for Deno. Supported discovery locations include PATH,
`~/.deno/bin/deno` (preferred on Ubuntu), `/usr/local/bin/deno`, and `/usr/bin/deno`.
If `xget` is not on PATH, use `~/.local/bin/xget` or add `~/.local/bin` to PATH.
An older `.venv` is retained for preservation but the new launcher uses `venv`.

Existing cookies, archives, sessions, settings and downloads are preserved.
Source cookies are copied only if no installed cookie file exists. The Ubuntu
uninstaller removes only the launcher and core, preserving data and environments.
The Windows installer also keeps existing cookies on reinstallation.

Menu 9 remains manual and confirms before updating. It upgrades Deno and
`yt-dlp[default]` (including EJS) in the current interpreter, then prints component
versions and readiness. Restart xGet after refreshing so newly installed Python
modules are loaded. Refresh performs no deletion of user data.
Menu 4 checks yt-dlp, FFmpeg, supported Deno and EJS before asking for URLs.
HTTP 403 diagnostics show installed component versions, possible causes and menu 9
guidance; they never refresh automatically. They cannot determine that a component
is the latest release without querying the network.

Menu 10 saves download and mirror paths in `xget-settings.json`; paths with spaces
are supported. An unavailable destination produces a warning and requires explicit
consent before using the default for that operation. The saved preference remains
unchanged. Conventional external mounts under `/mnt/<drive>`,
`/media/<user>/<drive>` and `/run/media/<user>/<drive>` are checked before creating
directories, preventing writes beneath an absent mount. For nonstandard custom
mount layouts, ensure the volume is mounted before starting xGet.

No fixed YouTube request/per-video sleeps are configured. Four concurrent fragments,
five accumulated logged errors, successful-item archiving, completed-item skipping,
HTTP, URL lists, mirrors, Torrent/Magnet and resume behavior remain supported.

Validation: Python 3.12 compilation and 46 unittest tests passed on Windows.
Ubuntu/WSL was unavailable on the build machine: shell installer execution and
live Ubuntu MP4/M4A/MP3 downloads remain unverified. This package does not itself
update an Ubuntu machine; run the installer there and verify the version output.

## 2.15.0 Torrent controls and batch YouTube reliability (2026-11-01)

Based on xGet 2.14.0. Both Windows and Ubuntu install the same xget.py core.
Torrent preview/select, persistent transfer limits, optional seeding and peer
controls were added without replacing aria2 or yt-dlp. Multi-URL and playlist
YouTube downloading, auto-resume archive, cookies and manual component refresh
are preserved. This build was tested with mock subprocesses and local unit
tests. Live Windows/Ubuntu Torrent and YouTube transfers need user testing.