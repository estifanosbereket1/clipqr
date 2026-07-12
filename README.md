# ClipQR

A clipboard manager for Ubuntu/Linux Mint with a tray icon, a global hotkey, and a QR-code feature for copying clipboard entries directly to your phone's clipboard by scanning. Includes LAN peer sync, clipboard diffing, content-type detection, and more.

## Features

- System tray clipboard history with pin, delete, copy, and search
- Scan a QR code to auto-copy any entry to your phone's clipboard (HTTPS, local network only)
- Global hotkey to open the history window (works on both X11 and Wayland)
- Automatic content-type detection (JSON, JWT, URLs, UUIDs, code snippets, etc.)
- Staleness warnings on older entries
- Burn-after-copy for sensitive one-time values
- Line-level diffing between clipboard entries
- Visual clipboard playback timeline
- LAN peer sync — automatically discover and sync clipboard history with other ClipQR instances on your network
- Fully configurable: history limit, poll interval, port, playback mode

## Prerequisites

- Ubuntu 22.04+, Linux Mint, or another GTK3-based Linux desktop
- Python 3.10+
- A desktop environment with a system tray (Ubuntu ships this by default; other GNOME-based distros may need the "AppIndicator and KStatusNotifierItem Support" extension)

## 1. System dependencies

```bash
sudo apt update
sudo apt install \
  python3-venv python3-pip git \
  python3-gi gir1.2-gtk-3.0 gir1.2-ayatanaappindicator3-0.1 \
  xclip \
  libnss3-tools
```

- `python3-gi` / `gir1.2-gtk-3.0` / `gir1.2-ayatanaappindicator3-0.1` — GTK3 and tray icon bindings
- `xclip` — required by the clipboard read/write library on X11 (for Wayland, use `wl-clipboard` instead)
- `libnss3-tools` — required by `mkcert` for managing trusted certificates

## 2. Install mkcert

ClipQR uses [mkcert](https://github.com/FiloSottile/mkcert) to generate locally-trusted HTTPS certificates, required for the phone's browser to auto-copy via the Clipboard API.

```bash
curl -JLO "https://dl.filippo.io/mkcert/latest?for=linux/amd64"
chmod +x mkcert-v*-linux-amd64
sudo mv mkcert-v*-linux-amd64 /usr/local/bin/mkcert
mkcert -install
```

`mkcert -install` creates a local Certificate Authority (CA) and trusts it on this machine. You'll separately trust it on your phone later (see step 7).

## 3. Clone and set up the project

GTK bindings are system packages, not pip packages, so the virtual environment needs `--system-site-packages` to see them:

```bash
git clone <this-repo-url> clipqr
cd clipqr
python3 -m venv venv --system-site-packages
source venv/bin/activate
pip install -r requirements.txt
```

## 4. First run

```bash
python3 main.py
```

On first run, ClipQR will:
- Create its database at `~/.local/share/clipqr/history.db`
- Create its settings file at `~/.config/clipqr/settings.json`
- Detect your LAN IP and generate an HTTPS certificate for it automatically (via `mkcert`)
- Start the tray icon, clipboard monitor, and local HTTPS server

You should see a tray icon appear. Click it to see the menu: **Open Clipboard History**, **Settings**, **Clipboard Playback**, **Peer Devices**, and **Quit**.

## 5. Set up the global hotkey

Global hotkeys work differently depending on whether you're on X11 or Wayland — ClipQR handles this automatically via a Unix signal, but you need to register the actual key combination once:

1. Open **Settings** from the tray menu
2. Click into the "Press a key combo..." field and press your desired combination (e.g. `Ctrl+Alt+V`)
3. If it says "Available," click **Save Shortcut**
4. If it says "Already used by...", pick a different combination

This registers a custom GNOME keyboard shortcut that signals the running ClipQR process to open the history window.

## 6. Set up autostart (optional, recommended)

To have ClipQR start automatically on login and restart if it crashes:

```bash
mkdir -p ~/.config/systemd/user
```

Create `~/.config/systemd/user/clipqr.service`:

```ini
[Unit]
Description=ClipQR clipboard manager
After=graphical-session.target
PartOf=graphical-session.target

[Service]
Type=simple
ExecStart=/path/to/clipqr/venv/bin/python3 /path/to/clipqr/main.py
WorkingDirectory=/path/to/clipqr
Restart=on-failure
RestartSec=3

[Install]
WantedBy=graphical-session.target
```

Replace `/path/to/clipqr` with your actual project path (run `pwd` inside the project folder to get it).

```bash
systemctl --user daemon-reload
systemctl --user enable clipqr.service
systemctl --user start clipqr.service
```

Check it's running:
```bash
systemctl --user status clipqr.service
```

## 7. Set up your phone

1. Make sure your phone is on the **same Wi-Fi network** as your computer
2. In ClipQR's Settings window, click **Show CA Setup QR**
3. Scan it with your phone — this downloads a certificate file
4. On Android: **Settings → Security → Encryption & credentials → Install a certificate → CA certificate**, then select the downloaded file
   - This is a one-time step per phone. It's required because Android blocks direct one-tap installation of CA certificates from downloaded files as a security measure.
5. Once trusted, click the QR-code icon on any clipboard history entry and scan it with your phone — the content should auto-copy to your phone's clipboard

## 8. LAN peer sync (optional)

To sync clipboard history between two computers on the same network:

1. Run ClipQR on both machines (steps 1–4 above, on each)
2. Open **Peer Devices** from the tray menu on both machines
3. Each machine should discover the other automatically within a few seconds and list it under "Pending"
4. Click **Approve** on both sides to pair
5. Clipboard entries will now sync automatically, both directions, excluding pinned and self-destruct entries

## Configuration

All settings are available in the Settings window, or editable directly at `~/.config/clipqr/settings.json`:

| Setting | Description | Default |
|---|---|---|
| `history_limit` | Max entries shown in Recent (live, no restart needed) | 50 |
| `poll_interval` | Clipboard check frequency in seconds (restart required) | 1.0 |
| `port` | Local HTTPS server port (restart required) | 8000 |
| `playback_mode` | `"time"` (visual timeline) or `"index"` (simple slider) | `"time"` |

## Known limitations

- **LAN only.** Phone sync and peer sync require devices to be on the same local network. This is a deliberate design choice to keep clipboard data off any third-party servers.
- **Self-signed certificates.** Since there's no public domain involved, each machine generates its own certificate. Phones need a one-time manual trust step (see step 7); peer-to-peer sync between computers skips certificate verification entirely, since both ends are your own trusted devices.
- **IP changes.** If your computer's LAN IP changes (new network, DHCP lease renewal), ClipQR detects this automatically and regenerates its certificate. Peers will re-discover the new address within a few seconds; phone QR codes generated before an IP change will stop working and need to be regenerated (just reopen the QR for that entry).
- **Wayland hotkey limitation.** Global hotkey capture libraries generally don't work on Wayland for security reasons. ClipQR works around this by having GNOME run a shell command (`kill -SIGUSR1 ...`) on your registered key combo, which signals the running process — this works on both X11 and Wayland, but does mean the hotkey is registered as a GNOME custom shortcut rather than being captured directly by the app.

## Project structure

```
storage.py            # SQLite persistence layer
clipboard_monitor.py  # background clipboard watcher
history_window.py     # main GTK history UI
qr_popup.py           # QR code generation
qr_display.py         # QR popup window
qr_server.py          # FastAPI HTTPS server for phone auto-copy
hotkey.py              # Wayland-proof signal-based hotkey listener
gnome_shortcuts.py     # GNOME custom keybinding registration
settings_store.py      # JSON-backed app settings
settings_window.py     # settings UI
cert_manager.py        # mkcert certificate generation
tray.py                 # system tray icon and menu
peer_discovery.py      # mDNS peer discovery
peer_store.py           # peer pairing state
peer_sync.py            # peer-to-peer sync protocol
peer_window.py          # peer pairing UI
content_detector.py     # clipboard content-type detection
diff_utils.py            # text diffing logic
diff_display.py          # diff popup window
clipboard_wipe.py        # delayed clipboard-wipe for burn-after-copy
playback_window.py       # clipboard playback UI
timeline_widget.py       # custom-drawn playback timeline
icon_loader.py            # bundled SVG icon loader
main.py                    # entry point, wires everything together
```
