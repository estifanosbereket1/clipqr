import os
import threading

import gi
import uvicorn

from clipboard_monitor import start_monitoring
from history_window import HistoryWindow, open_qr_popup
from hotkey import setup_signal_listener
from qr_server import app as qr_app
from settings_window import SettingsWindow
from storage import init_db
from tray import setup_tray_icon

gi.require_version("Gtk", "3.0")
from gi.repository import GLib, Gtk


def main():
    init_db()

    from cert_manager import get_cert_dir, regenerate_cert_for_ip
    from settings_store import check_ip_changed, load_settings, save_settings

    changed, old_ip, new_ip = check_ip_changed()
    if changed and new_ip:
        print(f"LAN IP changed ({old_ip} -> {new_ip}), regenerating certificate...")
        regenerate_cert_for_ip(new_ip)
        save_settings({"last_known_ip": new_ip})

    settings = load_settings()
    cert_dir = get_cert_dir()
    cert_path = str(cert_dir / "cert.pem")
    key_path = str(cert_dir / "key.pem")

    def on_clipboard_changed():
        GLib.idle_add(history_window.refresh)

    threading.Thread(
        target=start_monitoring,
        kwargs={
            "poll_interval": settings["poll_interval"],
            "on_change": on_clipboard_changed,
        },
        daemon=True,
    ).start()

    threading.Thread(
        target=uvicorn.run,
        kwargs={
            "app": qr_app,
            "host": "0.0.0.0",
            "port": settings["port"],
            "ssl_keyfile": key_path,
            "ssl_certfile": cert_path,
        },
        daemon=True,
    ).start()

    history_window = HistoryWindow(on_qr_clicked=open_qr_popup)

    def show_history_window():
        history_window.show_window()

    def on_hotkey_triggered():
        GLib.idle_add(show_history_window)

    setup_signal_listener(on_hotkey_triggered)

    def quit_app():
        pid_file = "/tmp/clipqr.pid"
        if os.path.exists(pid_file):
            os.remove(pid_file)
        Gtk.main_quit()

    def open_settings():
        SettingsWindow()

    indicator = setup_tray_icon(
        on_open=show_history_window, on_settings=open_settings, on_quit=quit_app
    )

    Gtk.main()


if __name__ == "__main__":
    main()
