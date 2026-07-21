# ClipVault

A clipboard manager for Ubuntu/Linux Mint with a tray icon, a global hotkey, and a QR-code feature for copying clipboard entries directly to your phone by scanning. Includes LAN peer sync, clipboard diffing, content-type detection, theming, and more , all fully local, nothing ever touches a cloud server.

**Your clipboard, everywhere. Never in the cloud.**

## Features

- System tray clipboard history with pin, delete, copy, and fuzzy search
- Scan a QR code to auto-copy any entry to your phone's clipboard (local HTTPS, LAN only)
- Global hotkey to open the history window (works on both X11 and Wayland)
- Automatic content-type detection (JSON, JWT, URLs, UUIDs, code snippets, etc.) with badges
- Staleness warnings on older entries
- Burn-after-copy for sensitive one-time values (auto-wipes clipboard after use)
- Line-level diffing between clipboard entries , chronological or any two you pick
- Visual clipboard playback timeline
- LAN peer sync , automatically discover and sync clipboard history with your other devices
- QR-to-QR chaining for offline device-to-device sharing
- Full theming system (multiple dark/light palettes, auto-matches your system theme)
- First-run setup wizard, auto-updates, and a clean uninstaller
- Fully configurable: history limit, poll interval, port, playback mode

## Install

Build and install the `.deb` package:

```bash
git clone https://github.com/estifanosbereket1/clipvault.git
cd clipvault
./packaging/build-deb.sh
sudo apt install ./clipvault_*.deb
```

`apt install ./file.deb` (rather than `dpkg -i`) resolves and installs ClipVault's system dependencies (GTK bindings, `xclip`, etc.) automatically. The package sets up a Python virtual environment and a local HTTPS certificate authority the first time it's installed, and registers a systemd user service so ClipVault starts on login and restarts if it crashes.

After installing, log out and back in, or start it immediately with:

```bash
systemctl --user start clipvault.service
```

The first time it runs, a setup wizard will walk you through choosing a theme, a port, hotkey, and phone access , all in under a minute.

To update to a newer version, rebuild the `.deb` from an updated checkout and `apt install` it again — `apt` treats it as an upgrade in place.

See `packaging/README.md` for how the package is put together and how to test it before installing.

### Legacy source install (deprecated)

Before the `.deb` existed, ClipVault was installed by cloning the repo and running a script that set up a venv directly in place. This still works but is no longer the recommended path — it doesn't give you a real install/uninstall, and the run-from-source model is exactly what packaging above was built to replace.

```bash
curl -fsSL https://raw.githubusercontent.com/estifanosbereket1/clipvault/main/bootstrap.sh | bash
```

or, step by step:

```bash
git clone https://github.com/estifanosbereket1/clipvault.git
cd clipvault
chmod +x install.sh
./install.sh
```

## First run

The setup wizard walks you through:
1. A quick intro to what ClipVault does
2. Choosing a color theme (only palettes matching your system's dark/light mode are shown)
3. Picking a port for the local HTTPS server (auto-checks for availability)
4. Setting up phone access (scan a QR to trust this computer, one time per phone)
5. Setting your global hotkey

After that, you'll see the ClipVault icon in your system tray. Click it for the full menu: Open Clipboard History, Clipboard Playback, Peer Devices, Settings, Check for Updates, About, and Uninstall.

## Phone setup

If you skipped it during onboarding, or want to trust a new phone later:
1. Make sure your phone is on the same Wi-Fi network as your computer
2. Open **Settings** from the tray menu → **Show CA Setup QR**
3. Scan it with your phone —> this downloads a certificate file
4. On Android: **Settings → Security → Encryption & credentials → Install a certificate → CA certificate**, then select the downloaded file (this is a one-time step per phone —> Android requires it to be done manually as a security measure)
5. Once trusted, click the QR icon on any clipboard entry and scan it —> the content auto-copies to your phone's clipboard

## LAN peer sync

To sync clipboard history between two of your own computers on the same network:
1. Run ClipVault on both machines
2. Open **Peer Devices** from the tray menu on each —> they'll discover each other automatically within a few seconds
3. Click **Approve** on both sides to pair
4. Clipboard entries sync automatically both ways from then on (pinned and self-destruct entries are never synced)

## Updating

ClipVault checks GitHub Releases for new versions. Click **Check for Updates** in the tray menu , if one's available, it'll pull the latest code, reinstall dependencies, and restart automatically. Your clipboard history and settings are never touched by an update.

## Uninstalling

Click **Uninstall ClipVault** in the tray menu — it removes your GNOME hotkey, asks whether to keep your clipboard history/settings, then runs `sudo apt remove clipvault`. You can also just run `sudo apt remove clipvault` yourself; your data at `~/.config/clipvault` and `~/.local/share/clipvault` is left in place either way unless you delete it manually.

(Legacy source installs: run `./uninstall.sh` from the project folder instead.)

## Configuration

All settings are available in the Settings window, or editable directly at `~/.config/clipvault/settings.json`:

| Setting | Description | Default |
|---|---|---|
| `history_limit` | Max entries shown in Recent (live, no restart needed) | 50 |
| `poll_interval` | Clipboard check frequency in seconds (restart required) | 1.0 |
| `port` | Local HTTPS server port (restart required) | 8000 |
| `playback_mode` | `"time"` (visual timeline) or `"index"` (simple slider) | `"time"` |
| `dark_palette` / `light_palette` | Active theme per system mode | `"midnight"` / `"daylight"` |

## Known limitations

- **LAN only.** Phone sync and peer sync require devices to be on the same local network , a deliberate choice to keep clipboard data off any third-party server.
- **Self-signed certificates.** Each machine generates its own certificate. Phones need a one-time manual trust step; peer-to-peer sync between your own computers skips certificate verification entirely, since both ends are your own trusted devices.
- **IP changes.** If your computer's LAN IP changes, ClipVault detects this automatically and regenerates its certificate. Existing phone QR codes will need to be regenerated (just reopen the QR for that entry) since they encode the old IP.
- **Wayland hotkey limitation.** ClipVault works around Wayland's global-hotkey restrictions by having GNOME run a shell command on your registered key combo, which signals the running process. This works on both X11 and Wayland.

## For developers

Project structure:

```
storage.py             # SQLite persistence layer
clipboard_monitor.py   # background clipboard watcher
history_window.py      # main GTK history UI
qr_popup.py            # QR code generation
qr_display.py          # QR popup window
qr_server.py            # FastAPI HTTPS server for phone auto-copy
hotkey.py               # Wayland-proof signal-based hotkey listener
gnome_shortcuts.py      # GNOME custom keybinding registration
settings_store.py       # JSON-backed app settings
settings_window.py      # settings UI
onboarding_wizard.py    # first-run setup wizard
cert_manager.py         # mkcert certificate generation
tray.py                 # system tray icon and menu
peer_discovery.py       # mDNS peer discovery
peer_store.py           # peer pairing state
peer_sync.py            # peer-to-peer sync protocol
peer_window.py          # peer pairing UI
content_detector.py     # clipboard content-type detection
diff_utils.py           # text diffing logic
diff_display.py         # diff popup window
clipboard_wipe.py       # delayed clipboard-wipe for burn-after-copy
playback_window.py      # clipboard playback UI
timeline_widget.py      # custom-drawn playback timeline
palettes.py             # color palette definitions
theme_manager.py        # CSS theming + system dark/light detection
palette_picker.py       # theme selection UI
icon_loader.py          # bundled SVG icon loader
about_window.py         # About window
update_checker.py       # GitHub Releases-based update checker
port_checker.py         # port availability checking for onboarding
main.py                 # entry point, wires everything together
VERSION                 # version string; also read at runtime (see packaging/root/usr/bin/clipvault)
packaging/              # .deb build (packaging/build-deb.sh); see packaging/README.md
install.sh              # legacy source installer (deprecated, see Install section)
bootstrap.sh            # legacy curl-friendly install entrypoint (deprecated)
uninstall.sh            # legacy source uninstaller (deprecated)
```

Setting `GITHUB_TOKEN` as an environment variable raises the update checker's rate limit from 60 to 5000 requests/hour , useful during development, not required for normal use.
