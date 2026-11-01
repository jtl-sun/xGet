#!/usr/bin/env bash
set -euo pipefail
# Remove only program entry points; retain user data and Python environments.
rm -f -- "$HOME/.local/bin/xget" "$HOME/.local/share/xget/xget.py"
echo "xGet program removed. User data and environments were preserved in ~/.local/share/xget."