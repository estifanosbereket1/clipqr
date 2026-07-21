#!/bin/bash
# ClipVault (.deb install) uninstall helper, launched from the tray menu.
# Handles what apt/dpkg can't safely automate (per-user data, the GNOME
# hotkey), then hands off to apt for the actual package removal.
set -e

APP_DIR=/usr/share/clipvault
VENV_PY=/var/lib/clipvault/venv/bin/python3

echo "=== ClipVault Uninstaller ==="
echo ""

echo "--- Removing the GNOME custom hotkey (if set) ---"
if [ -x "$VENV_PY" ]; then
    "$VENV_PY" -c "
import sys
sys.path.insert(0, '$APP_DIR')
try:
    from gnome_shortcuts import find_shortcut_by_name, unregister_custom_shortcut
    existing = find_shortcut_by_name('Open ClipVault')
    if existing:
        path, _ = existing
        unregister_custom_shortcut(path)
        print('Hotkey removed.')
    else:
        print('No hotkey found, skipping.')
except Exception as e:
    print(f'Could not remove hotkey automatically: {e}')
" 2>/dev/null || echo "Could not remove hotkey automatically."
else
    echo "Skipping (ClipVault's venv is already gone)."
fi

echo ""
read -p "Delete your clipboard history and settings too? This cannot be undone. [y/N] " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Yy]$ ]]; then
    rm -rf "$HOME/.config/clipvault"
    rm -rf "$HOME/.local/share/clipvault"
    echo "Clipboard history and settings deleted."
else
    echo "Keeping your data at ~/.config/clipvault and ~/.local/share/clipvault."
fi

echo ""
echo "--- Removing the ClipVault package ---"
echo "This needs your password to run: sudo apt remove clipvault"
sudo apt remove clipvault

echo ""
echo "=== ClipVault has been uninstalled. ==="
read -p "Press Enter to close this window."
