# xGet 2.11.0

xGet is a menu-driven integrated terminal downloader for Windows and Ubuntu.

## Features

- Download a direct HTTP/HTTPS file
- Download supported public OneDrive sharing URLs
- Download multiple files from a TXT URL list
- Resume interrupted downloads
- Mirror a web page or an entire website on the same domain
- Download YouTube videos, playlists, channels, MP3 audio, and M4A audio
- Download multiple YouTube URLs concurrently
- Automatically use a local `cookies.txt` file
- Clean incomplete download files
- Manually refresh Deno, yt-dlp Nightly, and EJS without changing cookies
- Download one or multiple `.torrent` files and Magnet links concurrently
- Automatically repair missing Python modules
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

## Automatic Storage Locations

xGet creates the following directories next to `xget.py`:

```text
xGet/
├── xget.py
├── downloads/   Direct files, URL lists, YouTube, Torrent, and Magnet downloads
└── home/        Mirrored web pages and websites
```

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
0. Exit
```

## Website Mirroring

xGet downloads HTML, images, CSS, JavaScript, and internal page links, then
rewrites supported links for local browsing. Content that requires login, DRM,
server-side processing, infinite scrolling, or complex JavaScript may not be
fully available offline.

Respect each website's terms of service and copyright requirements.

## YouTube Downloads

Use this feature only for content that you own or are authorized to download.
Keep `yt-dlp` current to accommodate YouTube changes.

The default YouTube download format is M4A audio. MP4 video and MP3 audio
remain available from the format menu. M4A is preferred directly from YouTube
and FFmpeg finalizes the file as M4A when conversion is required.

For MP3, yt-dlp continues to show the normal download percentage. When FFmpeg
starts, xGet displays `MP3 CONVERSION`, the playlist item number, a live spinner,
and elapsed time until it reaches `100% - completed`. This prevents a long audio
conversion from looking like the program has stopped.

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
