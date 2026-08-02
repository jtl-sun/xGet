#!/usr/bin/env bash
set -euo pipefail

rm -f "$HOME/.local/bin/xget"
if [ -d "$HOME/.local/share/xget" ]; then
    find "$HOME/.local/share/xget" -depth -delete
fi
echo "xGet was removed. Shared download tools were kept."
