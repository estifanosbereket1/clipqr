#!/bin/bash
set -e

echo "=== ClipVault Installer ==="
echo ""

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
echo "Installing ClipVault from: $PROJECT_DIR"
echo ""

detect_package_manager() {
    if command -v apt &> /dev/null; then
        echo "apt"
    elif command -v pacman &> /dev/null; then
        echo "pacman"
    elif command -v dnf &> /dev/null; then
        echo "dnf"
    else
        echo "unknown"
    fi
}

PKG_MANAGER=$(detect_package_manager)
echo "Detected package manager: $PKG_MANAGER"
echo ""

if [ "$PKG_MANAGER" == "unknown" ]; then
    echo "⚠ Couldn't detect apt, pacman, or dnf on this system."
    echo "  Please install these manually before continuing:"
    echo "  - Python 3 with venv/pip"
    echo "  - GTK3 + Python GObject bindings (PyGObject)"
    echo "  - libappindicator/ayatana-appindicator (for the tray icon)"
    echo "  - xclip (or wl-clipboard on Wayland)"
    echo "  - NSS tools (required by mkcert)"
    echo "  - git"
    read -p "Press Enter once these are installed, or Ctrl+C to stop and do it now. "
else
    read -p "Install system dependencies now using $PKG_MANAGER? [Y/n] " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Nn]$ ]]; then
        echo "--- Installing system dependencies ---"
        case "$PKG_MANAGER" in
            apt)
                sudo apt update
                sudo apt install -y \
                    python3-venv python3-pip git \
                    python3-gi gir1.2-gtk-3.0 gir1.2-ayatanaappindicator3-0.1 \
                    xclip \
                    libnss3-tools
                ;;
            pacman)
                sudo pacman -Syu --needed --noconfirm \
                    python python-pip git \
                    python-gobject gtk3 libappindicator-gtk3 \
                    xclip \
                    nss
                ;;
            dnf)
                sudo dnf install -y \
                    python3-pip git \
                    python3-gobject gtk3 \
                    xclip \
                    nss-tools
                echo ""
                echo "⚠ Fedora's default repos may not include Ayatana AppIndicator support."
                echo "  If the tray icon doesn't appear after install, you may need:"
                echo "  sudo dnf copr enable alebastr/kde-gtk-config"
                echo "  or check https://extensions.gnome.org/extension/615/appindicator-support/"
                ;;
        esac
        echo "System dependencies installed."
    else
        echo "Skipping automatic dependency install -- make sure they're installed manually."
    fi
fi

echo ""
echo "--- Setting up Python virtual environment ---"

VENV_DIR="$PROJECT_DIR/venv"

if [ -d "$VENV_DIR" ]; then
    echo "Virtual environment already exists, skipping creation."
else
    python3 -m venv "$VENV_DIR" --system-site-packages
    echo "Virtual environment created."
fi

echo "Installing Python dependencies..."
"$VENV_DIR/bin/pip" install --upgrade pip
"$VENV_DIR/bin/pip" install -r "$PROJECT_DIR/requirements.txt"

echo "Python dependencies installed."

echo ""
echo "--- Setting up mkcert (for HTTPS certificates) ---"

if command -v mkcert &> /dev/null; then
    echo "mkcert already installed, skipping."
else
    echo "Installing mkcert..."
    TMP_MKCERT="$(mktemp)"
    curl -sJL "https://dl.filippo.io/mkcert/latest?for=linux/amd64" -o "$TMP_MKCERT"
    chmod +x "$TMP_MKCERT"
    sudo mv "$TMP_MKCERT" /usr/local/bin/mkcert
    echo "mkcert installed."
fi

echo "Setting up local certificate authority..."
mkcert -install
echo "Certificate authority ready."

echo ""
echo "--- Setting up autostart (systemd) ---"

SYSTEMD_DIR="$HOME/.config/systemd/user"
mkdir -p "$SYSTEMD_DIR"

cat > "$SYSTEMD_DIR/clipvault.service" <<EOF
[Unit]
Description=ClipVault clipboard manager
After=graphical-session.target
PartOf=graphical-session.target

[Service]
Type=simple
ExecStart=$VENV_DIR/bin/python3 $PROJECT_DIR/main.py
WorkingDirectory=$PROJECT_DIR
Restart=on-failure
RestartSec=3

[Install]
WantedBy=graphical-session.target
EOF

systemctl --user daemon-reload
systemctl --user enable clipvault.service

echo "Autostart configured. ClipVault will start automatically on login."

echo ""
echo "--- Setting up application launcher ---"

APPS_DIR="$HOME/.local/share/applications"
mkdir -p "$APPS_DIR"

cat > "$APPS_DIR/clipvault.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=ClipVault
Comment=Clipboard manager with QR-to-phone sync
Exec=$VENV_DIR/bin/python3 $PROJECT_DIR/main.py
Icon=$PROJECT_DIR/assets/icons/app-icon.png
Terminal=false
Categories=Utility;
StartupNotify=true
EOF

update-desktop-database "$APPS_DIR" 2>/dev/null || true

echo "Application launcher created. ClipVault is now available in your app menu."

echo ""
echo "=== Installation complete! ==="
echo ""
echo "Starting ClipVault now..."
systemctl --user start clipvault.service
echo "Done. Look for the ClipVault icon in your system tray."
