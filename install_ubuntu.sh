#!/usr/bin/env bash
set -euo pipefail
source_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
install_dir="$HOME/.local/share/xget"
bin_dir="$HOME/.local/bin"
echo "xGet Ubuntu installer"
sudo apt-get update
sudo apt-get install -y python3 python3-venv python3-tk aria2 ffmpeg curl unzip
mkdir -p "$install_dir" "$bin_dir"
# Replace only program files. Preserve user data and existing cookies.
if [ "$source_dir/xget.py" != "$install_dir/xget.py" ]; then
    install -m 755 "$source_dir/xget.py" "$install_dir/xget.py"
fi
if [ -f "$source_dir/cookies.txt" ] && [ ! -e "$install_dir/cookies.txt" ]; then
    install -m 600 "$source_dir/cookies.txt" "$install_dir/cookies.txt"
fi
python3 -m venv "$install_dir/venv"
python="$install_dir/venv/bin/python"
"$python" -m pip install --upgrade pip --pre "yt-dlp[default]" requests beautifulsoup4
# Validate using the same core, without relying on a reloaded shell PATH.
"$python" - "$install_dir/xget.py" <<'PY'
import importlib.util
import sys
spec = importlib.util.spec_from_file_location("xget", sys.argv[1])
app = importlib.util.module_from_spec(spec)
spec.loader.exec_module(app)
version = app.deno_version()
if not version or tuple(map(int, version.split('.'))) < app.DENO_MIN_VERSION:
    if not app.refresh_deno():
        raise SystemExit("Deno installation failed; fix the reported error and retry.")
if not app.youtube_preflight():
    raise SystemExit("YouTube components are not ready; installation verification failed.")
PY
launcher="$bin_dir/xget"
cat > "$launcher" <<'SH'
#!/usr/bin/env bash
exec "$HOME/.local/share/xget/venv/bin/python" "$HOME/.local/share/xget/xget.py" "$@"
SH
chmod +x "$launcher"
expected="$("$python" "$source_dir/xget.py" --version)"
installed="$("$launcher" --version)"
if [ "$installed" != "$expected" ]; then
    echo "ERROR: installed version differs from release: $installed / $expected" >&2
    exit 1
fi
echo "Installed xGet version: ${installed##* }"
echo "Installation complete. Run: $bin_dir/xget"
echo 'If xget is not on PATH, add ~/.local/bin to PATH or use the full command above.'