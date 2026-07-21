# Building the ClipVault `.deb`

```
./packaging/build-deb.sh
```

Produces `clipvault_<version>_all.deb` at the repo root, versioned from the top-level `VERSION` file.

## Design notes

- **No `debhelper`/`dh_make`.** This isn't going into the official Debian archive, so the package is a manually-assembled `DEBIAN/` control directory built with `dpkg-deb --build`. Keeps the whole thing legible in one place (`packaging/debian/`, `packaging/root/`) instead of pulling in the full Debian packaging toolchain.
- **Pip dependencies install at package-install time, not build time.** `postinst` creates a venv at `/var/lib/clipvault/venv` with `--system-site-packages` (so it can see the apt-installed PyGObject/GTK bindings) and runs `pip install -r requirements.txt` there. This mirrors what `install.sh` did before, just as a proper maintainer script. It does mean `apt install` needs network access the first time.
- **Venv lives under `/var/lib/clipvault`, not `/usr/share/clipvault`.** `/usr/share/clipvault` is the dpkg-owned static payload (tracked by `dpkg -L`, restored verbatim on reinstall); the venv is generated content that changes per-machine. Keeping them apart means `postrm` can cleanly delete the venv without dpkg ever being confused about which files it "owns."
- **`mkcert` is vendored, not downloaded at install time.** The build script downloads the `linux/amd64` binary once (cached in `packaging/vendor/`, gitignored) and ships it inside the package at `/usr/share/clipvault/vendor/mkcert`. `postinst` symlinks it onto `PATH` only if the system doesn't already have an `mkcert`. This is a deliberate, minor deviation from Debian policy — an `Architecture: all` package nominally shouldn't contain an arch-specific binary — accepted here because this isn't going to the official archive and the project only targets Ubuntu/GNOME desktops (effectively amd64).
- **`mkcert -install` (trusting the local CA) is NOT run by postinst.** It has to run as the real desktop user, not root, since it writes into that user's CA/NSS/browser trust stores. `cert_manager.ensure_ca_installed()` runs it once per user on first app startup instead.
- **`postrm` never touches per-user state.** `~/.local/share/clipvault`, `~/.config/clipvault`, and the GNOME custom keybinding (dconf) are left alone on `remove` and `purge` alike — a root maintainer script has no correct way to reach into arbitrary users' home directories on a multi-user system. Users who want that gone use the in-app "Uninstall ClipVault" tray action, which prompts them directly.
- **`systemctl --global enable/disable` only registers/deregisters the user unit** — postinst/prerm have no D-Bus session to actually start or stop a running instance. A freshly installed ClipVault starts on next login; an upgraded/removed one keeps running until the user quits from the tray or logs out.

## Testing

Safe, no-privileges-needed checks:

```
dpkg-deb --info clipvault_*.deb
dpkg-deb -c clipvault_*.deb
```

Structural install/remove test in a throwaway container (validates `Depends:` resolution and that maintainer scripts run clean — expect the `systemctl --global` calls to no-op under `|| true` since `ubuntu:24.04`'s default entrypoint isn't systemd):

```
docker run --rm -it -v "$PWD:/pkg" ubuntu:24.04 bash
apt-get update
apt-get install -y /pkg/clipvault_*.deb
dpkg -L clipvault
apt-get remove -y clipvault
apt-get purge -y clipvault
```

A full install on a real GNOME desktop is needed to check the tray icon, hotkey registration, systemd user-session activation, and actual `mkcert -install` browser trust — that's invasive (writes to `/usr/share`, `/usr/bin`, `/usr/lib/systemd/user`, `/usr/local/bin/mkcert`, enables the unit for every local user) and is best done in a disposable VM, not casually on a daily-driver machine.
