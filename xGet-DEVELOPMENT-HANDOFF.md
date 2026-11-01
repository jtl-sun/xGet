# xGet 2.15.0 Development Handoff

Date: 2026-11-01. Source: user-provided xGet-2.14.0-English.zip.
This document replaces the stale handoff bundled with that ZIP. GitHub state and
installed Ubuntu state were not inspected or changed.

## Current release

The single xget.py core defines VERSION = "2.15.0". Windows and Ubuntu installers
copy that same file. Ubuntu launcher executes ~/.local/share/xget/venv/bin/python
with ~/.local/share/xget/xget.py and forwards all quoted arguments. Menu header,
CLI, installer verification, README and release ZIP agree on 2.15.0.
Older release numbers are historical, not alternate runtime versions.

## Changes

- Ubuntu installer preserves all existing data and cookie files; verifies both
  YouTube readiness and the installed launcher's source-matching version.
- Installs curl/unzip, checks Deno >= 2.3.0 and uses the official Deno installation
  script for a missing/unsupported binary. Direct path detection avoids shell reloads.
- User Deno takes priority on Ubuntu; PATH and standard system paths are supported.
- yt-dlp receives js_runtimes = {"deno": {"path": detected_path}} explicitly.
- Manual menu 9 installs/upgrades yt-dlp[default] with EJS in sys.executable and
  upgrades Deno. If a system Deno cannot upgrade, Ubuntu installs a user-owned binary.
- Preflight checks component versions and FFmpeg; missing/outdated Deno, missing
  EJS/yt-dlp or FFmpeg block menu 4 before URL processing. No automatic YouTube repair.
- Logger and exception handling provide HTTP 403 causes, local component status,
  cookie/session guidance and manual refresh instructions. Local version display
  does not establish whether a release is current on the network.
- Storage settings survive restarts. Conventional external mount availability
  is checked before creating folders; failure requires consent for default fallback.
  Nonstandard external mount layouts require the user to mount their volume first.
- Ubuntu uninstall now removes entry points only. Windows reinstall keeps cookies.
- Permission-denied optional tool discovery no longer crashes the application.

## Preserved behavior

No artificial request/per-video delays. Four concurrent fragments. Five cumulative
logged errors stop a run without resetting on success. Download archives and
existing media continue to support skipping completed items. Cookies, settings,
sessions, downloaded files and archives are not deleted by install/refresh.
HTTP/list downloads, website mirror, Torrent/Magnet and resume code remain present.

## Validation and limits

Python 3.12 on Windows: compilation passed; 46 tests passed (31 existing, 15 added).
One existing path expectation was made platform-neutral. New cases cover source/
launcher/version consistency, cookie preservation, uninstall preservation, home
Deno discovery, absent/versioned Deno, preflight success/failure/blocking, explicit
runtime path, absent delay options, 403 manual guidance, refresh data preservation,
storage with spaces/persistence, missing mounts and consent-based fallback.
Installer tests inspect script contracts; they are not end-to-end Ubuntu execution.
Ubuntu/WSL and Bash were unavailable. No live YouTube download was performed.
Do not claim a user's old Ubuntu installation has been replaced until it is installed.

Commands for Ubuntu validation:

```bash
python3 -m py_compile xget.py tests/test_xget.py tests/test_ubuntu_update.py
python3 -m unittest discover -s tests -v
bash ./install_ubuntu.sh
~/.local/bin/xget --version
~/.local/bin/xget
```

Complete manual Ubuntu verification: version/header; Deno/EJS/FFmpeg status;
public-URL MP4/M4A/MP3; menu 10 persistence across restarts; menu 9 after consent;
cookies/archive/session/settings/download checksums unchanged by refresh; absent
mount warning and declined/accepted fallback; reinstall over an old installation.
Restart after refresh to load newly installed Python modules.

Upstream references: https://github.com/yt-dlp/yt-dlp/wiki/EJS and
https://docs.deno.com/runtime/getting_started/installation/ .

## 2.15.0 upgrade (2026-11-01)

Based on 2.14.0. Add Torrent-only preference keys in `xget-settings.json`:
`torrent_concurrent`, `torrent_download_limit`, `torrent_upload_limit`,
`torrent_seed_time`, `torrent_seed_ratio`, `torrent_max_peers`. They are
validated before applying them to aria2. Single local `.torrent` input
shows `aria2c --show-files=true` and supports `--select-file` indexes.
Magnet and multi-source download run without file selection. Preserve
`--check-integrity` and `.aria2` resume state; menu 8 no longer removes
`.aria2` control files. `--bt-save-metadata=true` enables saving downloaded
Magnet metadata. YouTube accepts @TXT URL list input in addition to original
input, and schedules only the next URL upon job completion, protecting the
error-limit circuit breaker from a pre-queued backlog. Do not remove playlist,
archive, cookie, manual-refresh or 1-2 simultaneous URL worker support.

Use `python3 -m unittest discover -s tests -v` and `python3 -m py_compile
xget.py tests/test_xget.py tests/test_ubuntu_update.py tests/test_torrent_upgrade.py`.
Do live verification on Windows/Ubuntu with permitted legal downloads. The
portable qBittorrent/uTorrent installers supplied for reference were NOT
executed, embedded, or redistributed.