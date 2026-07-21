#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

VERSION="$(tr -d '[:space:]' < "$REPO_ROOT/VERSION")"
PKG_NAME="clipvault"
ARCH="all"
OUT_DEB="$REPO_ROOT/${PKG_NAME}_${VERSION}_${ARCH}.deb"

STAGE="$(mktemp -d)"
trap 'rm -rf "$STAGE"' EXIT

echo "Building ${PKG_NAME} ${VERSION} (${ARCH})"
echo "Staging in $STAGE"

# --- 1. Control files ----------------------------------------------------
mkdir -p "$STAGE/DEBIAN"
sed "s/@VERSION@/$VERSION/" "$SCRIPT_DIR/debian/control.in" > "$STAGE/DEBIAN/control"
install -m 755 "$SCRIPT_DIR/debian/postinst" "$STAGE/DEBIAN/postinst"
install -m 755 "$SCRIPT_DIR/debian/prerm"    "$STAGE/DEBIAN/prerm"
install -m 755 "$SCRIPT_DIR/debian/postrm"   "$STAGE/DEBIAN/postrm"

# --- 2. Static payload from packaging/root/ -------------------------------
mkdir -p "$STAGE/usr/bin" "$STAGE/usr/share/applications" \
         "$STAGE/usr/lib/systemd/user" "$STAGE/usr/share/clipvault"
cp -a "$SCRIPT_DIR/root/usr/." "$STAGE/usr/"
chmod 755 "$STAGE/usr/bin/clipvault"
chmod 755 "$STAGE/usr/share/clipvault/uninstall.sh"

# --- 3. App source from the repo ------------------------------------------
APP_DEST="$STAGE/usr/share/clipvault"
cp "$REPO_ROOT"/*.py "$APP_DEST/"
cp "$REPO_ROOT/requirements.txt" "$APP_DEST/"
cp "$REPO_ROOT/VERSION" "$APP_DEST/"
cp -a "$REPO_ROOT/assets" "$APP_DEST/"

# --- 4. mkcert (bundled binary, downloaded once and cached) --------------
VENDOR_DIR="$SCRIPT_DIR/vendor"
MKCERT_BIN="$VENDOR_DIR/mkcert-linux-amd64"
mkdir -p "$VENDOR_DIR"
if [ ! -f "$MKCERT_BIN" ]; then
    echo "Downloading mkcert (cached in packaging/vendor/ for future builds)..."
    curl -sJL "https://dl.filippo.io/mkcert/latest?for=linux/amd64" -o "$MKCERT_BIN"
    chmod +x "$MKCERT_BIN"
fi
mkdir -p "$APP_DEST/vendor"
cp "$MKCERT_BIN" "$APP_DEST/vendor/mkcert"
chmod 755 "$APP_DEST/vendor/mkcert"

# --- 5. Build --------------------------------------------------------------
find "$STAGE" -type d -exec chmod 755 {} \;
dpkg-deb --build --root-owner-group "$STAGE" "$OUT_DEB"

echo ""
echo "Built: $OUT_DEB"
