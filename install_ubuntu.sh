#!/usr/bin/env bash
set -euo pipefail

echo "xGet Ubuntu installer"

sudo apt-get update
sudo apt-get install -y python3 python3-venv python3-tk aria2 ffmpeg

install_dir="$HOME/.local/share/xget"
bin_dir="$HOME/.local/bin"
mkdir -p "$install_dir" "$bin_dir"
install -m 755 "$(dirname "$0")/xget.py" "$install_dir/xget.py"
if [ -f "$(dirname "$0")/cookies.txt" ]; then
    install -m 600 "$(dirname "$0")/cookies.txt" "$install_dir/cookies.txt"
fi
python3 -m venv "$install_dir/.venv"
"$install_dir/.venv/bin/python" -m pip install --upgrade pip yt-dlp requests beautifulsoup4

launcher="$bin_dir/xget"
printf '%s\n' '#!/usr/bin/env bash' \
    "exec \"$install_dir/.venv/bin/python\" \"$install_dir/xget.py\" \"\$@\"" \
    > "$launcher"
chmod +x "$launcher"

echo
echo "Installation complete."
echo "Open a new terminal and enter: xget"
echo "Run now: $bin_dir/xget"
